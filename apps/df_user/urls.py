from django.conf.urls import url
from df_user.views import RegisterView, ActiveView, LoginView, LogoutView

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 用户注册
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 用户激活
    url(r'^login$', LoginView.as_view(), name='login'),  # 用户登录
    url(r'^logout$', LogoutView.as_view(), name='logout'),  # 用户退出
]
