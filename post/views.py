# -*- coding: utf-8 -*-
import random
import cgi
import urllib
import json

from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.conf import settings

from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from django.db import IntegrityError

from PostingOnFacebook.post.models import Person


def index(request):
    # use RequestContext for Cross Site Request Forgery protection
    return render_to_response('post/index.html',
                             {},
                             context_instance=RequestContext(request))

def login(request):
    try:
        login_username = request.POST['username']
        login_password = request.POST['password']
    except MultiValueDictKeyError:
        # redirect to first login page
        return render_to_response('post/index.html',
                                  {},
                                  context_instance=RequestContext(request)) 


    if len(login_username) < 1:
        response_msg = 'Username should be longer than one charater. Please try again!'
        return render_to_response('post/index.html',
                                  {'message': response_msg},
                                  context_instance=RequestContext(request)) 

    # 1. login/signin on this service
    # 1.1 if this pserson is new, add new person and generate new api_access_key
    # 1.2 if this pserson is not new, check password
    # 1.2.1 if password is correct, do next step
    # 1.2.2 if password is incorrect, return login page
    try:
        person = Person.objects.get(username=login_username)
        if login_password == person.password:

            if person.fb_id is None or person.fb_access_token is None:
                # Error Case Handling
                # If you quit before callback is called during singin step,
                # database has a tuple that doesn't have fb_id and fb_access_token for login person
                # if fb_id and fb_access_token is empty, try to get them
                # 2. get facebook access token
                """ First step of process, redirect user to facebook, which redirects 
                to login-callback """

                # to identify the callback request
                request.session['posting_username'] = person.username
                request.session['is_login']  = True

                args = {
                    'client_id': settings.FACEBOOK_APP_ID,
                    'scope': settings.FACEBOOK_SCOPE,
                    'redirect_uri': request.build_absolute_uri(reverse('login-callback')),
                }

                return HttpResponseRedirect('https://www.facebook.com/dialog/oauth?'
                                              + urllib.urlencode(args))
            else:
                response_msg = 'Login succeeded! Welcome, ' + person.username + '!'
                return render_to_response('post/post.html',
                                          {'username': person.username, 
                                           'api_access_key': person.api_access_key,
                                           'message': response_msg},
                                           context_instance=RequestContext(request)) 
        else:
            response_msg = 'Password is incorrect! Please try again!'
            return render_to_response('post/index.html',
                                      {'message': response_msg},
                                      context_instance=RequestContext(request)) 

    except ObjectDoesNotExist:
        # new person
        new_person = Person(username=login_username, password=login_password)

        new_api_access_key = ''
        # api_access_key should be unique
        try:
            new_api_access_key = get_unique_api_access_key_for_Person()
        except Exception as inst:
            response_msg = 'Failed to generate a unique api access key! Please try again!'
            return render_to_response('post/index.html',
                                      {'message': response_msg},
                                      context_instance=RequestContext(request)) 

        new_person.api_access_key = new_api_access_key
        new_person.save()

        # 2. get facebook access token
        """ First step of process, redirect user to facebook, which redirects 
        to login-callback """

        # to identify the callback request
        request.session['posting_username'] = new_person.username

        args = {
            'client_id': settings.FACEBOOK_APP_ID,
            'scope': settings.FACEBOOK_SCOPE,
            'redirect_uri': request.build_absolute_uri(reverse('login-callback')),
        }

        return HttpResponseRedirect('https://www.facebook.com/dialog/oauth?'
                                    + urllib.urlencode(args))


def callback(request):
   # id of oauth request
    posting_username = ''
    if request.session.get('posting_username', False):
        posting_username = request.session['posting_username']
    else:
        response_msg = 'We\'re sorry! Something wrong... maybe session problem.  Please login/singin again!'
        return render_to_response('post/index.html',
                                  {'message': response_msg },
                                  context_instance=RequestContext(request))

    """ Second step of the login process.
    It reads in a code from Facebook, then redirects back to the home page. """
    code = request.GET.get('code')

 
    """ Reads in a Facebook code and asks Facebook if it's valid and what
    user it points to. """
    args = {
        'client_id': settings.FACEBOOK_APP_ID,
        'client_secret': settings.FACEBOOK_APP_SECRET,
        'redirect_uri': request.build_absolute_uri(
                                       reverse('login-callback')),
        'code': code,
    }

    # Get a legit access token
    target = urllib.urlopen(
                   'https://graph.facebook.com/oauth/access_token?'
                       + urllib.urlencode(args)).read()
    response = cgi.parse_qs(target)
    fb_access_token = response['access_token'][-1]

    # Read the user's profile information
    fb_profile = urllib.urlopen(
           'https://graph.facebook.com/me?access_token=%s' % fb_access_token)
    fb_profile = json.load(fb_profile)

    fb_user_id = fb_profile['id']

    try:
        posting_person = Person.objects.get(username=posting_username)
    except ObjectDoesNotExist:
        response_msg = 'We\'re sorry! Something wrong... maybe session problem.  Please login/singin again!'
        return render_to_response('post/index.html',
                                  {'message': response_msg },
                                  context_instance=RequestContext(request))

    posting_person.fb_access_token = fb_access_token
    posting_person.fb_id = fb_user_id
    try:
        posting_person.save() # update fb_access_token and fb_id
    except IntegrityError as inst:

        # existing person which has the same fb_id
        existing_person = Person.objects.get(fb_id=fb_user_id)
        response_msg = ( 'In this service, an user can have only a facebook account.'
                        + ' facebook id=' + str(existing_person.fb_id)
                        + ' is already used by username=' + existing_person.username
                        + '. And if your web browser loged in facebook,'
                        + ' please logout from facebook and try login/singin again!' )

        # delete posting_person
        posting_person.delete()

        return render_to_response('post/index.html',
                                  {'message': response_msg },
                                  context_instance=RequestContext(request))

    # from loggin process or sigin process
    is_login = request.session.get('is_login', False)
    
    response_msg = ''
    if is_login is True:
        response_msg = 'Login succeeded! welcome, ' + posting_person.username + '!'
    else:
        response_msg = 'Singin succeeded! welcome, ' + posting_person.username + '!'

    return render_to_response('post/post.html',
                              {'username': posting_person.username,
                               'api_access_key': posting_person.api_access_key,
                               'message': response_msg},

                               context_instance=RequestContext(request)) 

 
def get_unique_api_access_key_for_Person(max_count=10):
    new_api_access_key = ''
    count = 0
    while (count < max_count):
        new_api_access_key = api_access_key_generator()
        try:
            Person.objects.get(api_access_key=new_api_access_key)
        except ObjectDoesNotExist:
            return new_api_access_key

        count = count + 1

    # fail to get unique api access key for Person
    raise Exception('Failed to create a unique api access key')
    

def api_access_key_generator(size=30, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
    return ''.join(random.choice(allowed_chars) for x in range(size))


def post(request):

    posting_username = ''
    posting_msg  = ''
    posting_person = None

    try:
        posting_username = request.POST['username']
    except MultiValueDictKeyError:
        response_msg = 'We\'re sorry! Something wrong...  Please login/singin again!'
        return render_to_response('post/index.html',
                                  {'message': response_msg },
                                  context_instance=RequestContext(request))

    try:
        posting_person = Person.objects.get(username=posting_username)
    except ObjectDoesNotExist:
        response_msg = 'we\'re sorry! something wrong...  please login/singin again!'
        return render_to_response('post/index.html',
                                  {'message': response_msg },
                                  context_instance=RequestContext(request))

    try:
        posting_msg = request.POST['posting_msg']
    except MultiValueDictKeyError:
        response_msg = 'We\'re sorry! Something wrong...  Please login/singin again!'
        return render_to_response('post/index.html',
                                  {'message': response_msg },
                                  context_instance=RequestContext(request))

    if len(posting_msg) == 0:
        response_msg = posting_username + '!, please write more than one character!'
        return render_to_response('post/post.html',
                                  {'username': posting_username,
                                   'message': response_msg},
                                  context_instance=RequestContext(request)) 

    fb_id = posting_person.fb_id
    fb_access_token = posting_person.fb_access_token

    if fb_access_token is None or fb_id is None:
        response_msg = 'we\'re sorry! something wrong...  please login/singin again!'
        return render_to_response('post/index.html',
                                  {'message': response_msg },
                                  context_instance=RequestContext(request))
    args = {
        'message': posting_msg,
    }

    post_data = {
        'id': fb_id,
        'access_token': fb_access_token,
    } 
    
    # POST method
    fb_feed_response = urllib.urlopen('https://graph.facebook.com/feed?' + urllib.urlencode(args),
                           urllib.urlencode(post_data))
    fb_posting_response = json.load(fb_feed_response)

    # TODO: ERROR Handling - access_token invalid, maybe need to update(re-generate) access_token
    response_msg = 'Posting succeeded! Do more!'
    return render_to_response('post/post.html',
                              {'api_access_key': None,
                               'message': response_msg,
                               'username': posting_username,
                               'fb_posting_response': fb_posting_response,
                               'fb_posting_message': posting_msg},
                              context_instance=RequestContext(request))
