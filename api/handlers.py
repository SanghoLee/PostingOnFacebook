from piston.handler import BaseHandler
from post.models import Person
from piston.utils import rc
from django.core.exceptions import ObjectDoesNotExist

import urllib
import json

class PostHandler(BaseHandler):
    allowed_methods = ('POST',)

    # Request/Reponse JSON Format
    # - Request : {"api_access_key":"key", "message":"input message to post facebook"}
    # - Response: {"id":"id"} 

    def create(self, request):
        data = request.data
        posting_api_access_key = data['api_access_key']
        posting_msg = data['message']

        try:
            posting_person = Person.objects.get(api_access_key=posting_api_access_key)
        except ObjectDoesNotExist:
            resp = rc.FORBIDDEN
            resp.write({"error":{"type":"ApiAccessKeyException", "message":"Invalid api_access_key. api_access_key=" + posting_api_access_key}})
            return resp
            
        posting_fb_id = posting_person.fb_id
        posting_fb_access_token = posting_person.fb_access_token

        # Access_token doesn't be issued yet
        if posting_fb_id is None or posting_fb_access_token is None:
            resp = rc.FORBIDDEN
            resp.write({"error": {"type":"OAuthException", "message":"access_token doesn't be issued yet. Please login first."}})
            return resp


        args = {
            'message': posting_msg,
        }

        post_data = {
            'id': posting_fb_id,
            'access_token': posting_fb_access_token,
        }

        # POST method
        fb_feed_response = urllib.urlopen('https://graph.facebook.com/feed?'
                         + urllib.urlencode(args),
                           urllib.urlencode(post_data))
        fb_posting_response = json.load(fb_feed_response)

        # Access_token is invalidated
        if 'error' in fb_posting_response:
            # delete invalid fb_access_token. we need to reissue access_token.
            posting_person.fb_id = None # just for clearing facebook info.
            posting_person.fb_access_token = None
            posting_person.save() # update row
            
            resp = rc.FORBIDDEN
            error_message = fb_posting_response['error']['message']
            error_message = error_message + ' The access_token is invalidated. Please login again.'
            fb_posting_response['error']['message'] = error_message
        else:
            resp = rc.CREATED

        resp.write(fb_posting_response)
        return resp
