from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'post.views.index', name='index'),
    url(r'^login/$', 'post.views.login', name='login'),
    url(r'^callback/$', 'post.views.callback', name='login-callback'),
    url(r'^post/$', 'post.views.post', name='post'),
)
