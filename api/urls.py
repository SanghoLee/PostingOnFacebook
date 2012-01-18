from django.conf.urls.defaults import patterns, include, url
from piston.resource import Resource
from PostingOnFacebook.api.handlers import PostHandler

post_handler = Resource(PostHandler)

urlpatterns = patterns('',
    url(r'^', post_handler),
)
