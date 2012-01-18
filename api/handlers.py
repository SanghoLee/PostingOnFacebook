from piston.handler import BaseHandler
from post.models import Person
from piston.utils import rc

import urllib
import json

class PostHandler(BaseHandler):
    allowed_methods = ('POST',)

    # Request/Reponse JSON Format
    # - Request : {"api_access_key":"key", "message":"input message to post facebook"}
    # - Response: {"id":"id"} 

    def create(self, request):
        if request.content_type:
            data = request.data
            posting_api_access_key = data['api_access_key']
            posting_msg = data['message']

            try:
                posting_person = Person.objects.get(api_access_key=posting_api_access_key)
            except ObjectDoesNotExist:
                resp = rc.FORBIDDEN
                resp.wirte('The api_access_key=' + posting_api_access_key + ' is not available.'
                           + ' Please sign in first.')
                return resp
            
            posting_fb_id = posting_person.fb_id
            posting_fb_access_token = posting_person.fb_access_token

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
            
            resp = rc.CREATED
            resp.write(fb_posting_response)
            return resp
        else:
            resp = rc.NOT_IMPLEMENTED
            return resp
