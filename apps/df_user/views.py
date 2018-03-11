from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View  # 导入视图类
from django.core.urlresolvers import reverse  # 导入反向解析重定向时调用函数
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired  # 导入加密类
from django.conf import settings  # 导入settings配置文件, 加密时需要使用SECRET_KEY
from celery_tasks.task import send_register_active_email  # 导入celery的任务函数
from django.contrib.auth import authenticate, login, logout # 对用户认证信息进行判断
from df_user.models import User
from redis import StrictRedis
import re


# Create your views here.
class RegisterView(View):
    def get(self, request):
        print('<<<<get>>>>>')
        return render(request, 'df_user/register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')

        register_html = 'df_user/register.html'

        # 验证数据完整性
        user_info = (username, password, email)
        if not all(user_info):
            return render(request, register_html, {'errmsg': '数据信息不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, register_html, {'errmsg': '邮箱格式错误'})

        # 根据用户名信息查找数据库
        try:
            # 从数据库中查找是否存在该用户
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user is not None:
            return render(request, register_html, {'errmsg': '该用户已存在'})

        """
        # 设置用户邮箱只可以注册一次, 校验用户之前邮箱是否已经注册过
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        if user is not None:
            return render(request, register_html, {'errmsg': '该邮箱已被注册'})
        """

        # 校验完成之后创建用户信息(账号/密码/邮箱)  用户登录认证
        user = User.objects.create_user(username, email, password)
        # 设置创建用户后设置激活状态为关闭, 只有通过emil连接激活
        user.is_active = 0
        user.save()

        # 向用户邮箱发送校验连接

        # 为了防止其他人其他人恶意请求,所以要对发送链接根据用户信息进行加密
        # 加密使用itsdangerous包
        # 1.创建加密对象(第一个参数是settings秘钥, 过期时间)
        serializer = Serializer(settings.SECRET_KEY, 300)
        # 2.加密后结果是bytes类型数据,需要进行转换后拼接到激活链接后
        token = serializer.dumps({'user_id': user.id}).decode()

        # 使用celery进行邮件发送,
        send_register_active_email.delay(email, username, token)

        # 返回应答: 跳转到首页
        return redirect(reverse('goods:index'))


# 通过接收用户点击链接进行激活
class ActiveView(View):
    # 用户点击邮箱链接属于Get请求
    def get(self, request, token):
        print(token)
        # 对于用户的url请求进行解密
        serializer = Serializer(settings.SECRET_KEY, 300)
        # 在此处
        try:
            # 通过用户的token解密后的数据,得到user_id
            user_info = serializer.loads(token)
            user_id = user_info['user_id']

            # 通过user_id可以查询到对应的用户
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 用户点击激活后,跳转到登录页面
            return redirect(reverse('user:login'))

        except SignatureExpired as err:
            return HttpResponse('激活链接已失效')


# 登录页面
class LoginView(View):
    def get(self, request):
        return render(request, 'df_user/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')
        # 数据完整性校验
        if not all([username, password]):
            return render(request, 'df_user/login.html', {'errmsg': '数据输入不完整'})

        # 登录校验 (使用系统认证系统函数)
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                print("用户已激活")

                # 使用认证系统记录用户登入状态
                login(request, user)

                # 登录成功直接进入首页
                return redirect(reverse('goods:index'))
            else:
                print('密码正确,但尚未激活')
                return render(request, 'df_user/login.html', {'errmsg': '邮件尚未激活'})
        else:
            print("账号密码错误")
            return render(request, 'df_user/login.html', {'errmsg': '账号密码错误'})


# 退出账户
class LogoutView(View):
    def get(self, request):
        # logout(request) 是django自带的登出函数,会清除登录者信息
        logout(request)
        return redirect(reverse('user:login'))


