from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View  # 导入视图类
from django.core.urlresolvers import reverse  # 导入反向解析重定向时调用函数
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired  # 导入加密类
from django.conf import settings  # 导入settings配置文件, 加密时需要使用SECRET_KEY
from celery_tasks.task import send_register_active_email  # 导入celery的任务函数
from django.contrib.auth import authenticate, login, logout  # 对用户认证信息进行判断
from utils.Mixin import LoginRequiredMixin
from django_redis import get_redis_connection
from df_user.models import User, Address
from df_goods.models import GoodsSKU
from df_order.models import OrderInfo, OrderGoods
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
        return redirect(reverse('df_goods:index'))


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
        username = request.COOKIES.get('username')
        checked = 'checked'
        if username is None:
            username = ''
            checked = ''
        return render(request, 'df_user/login.html', {'username': username, 'checked': checked})

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

                next_url = request.GET.get('next', reverse('df_goods:index'))
                response = redirect(next_url)

                if remember == 'on':
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')

                # 登录成功直接进入首页
                return response
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


# 跳转用户中心页面
class UserInfoView(LoginRequiredMixin, View):
    """用户中心-信息页"""

    def get(self, request):
        """显示"""
        # 获取登录用户
        user = request.user

        # 获取用户的默认收货地址
        address = Address.objects.get_default_address(user)

        # 获取用户的最近浏览商品的信息
        # from redis import StrictRedis
        # conn = StrictRedis(host='172.16.179.142', port=6379, db=5)

        # 返回StrictRedis类的对象
        conn = get_redis_connection('default')
        # 拼接key
        history_key = 'history_%d' % user.id

        # lrange(key, start, stop) 返回是列表
        # 获取用户最新浏览的5个商品的id
        sku_ids = conn.lrange(history_key, 0, 4)  # [1, 3, 5, 2]

        skus = []
        for sku_id in sku_ids:
            # 根据商品的id查询商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 追加到skus列表中
            skus.append(sku)

        # 组织模板上下文
        context = {
            'address': address,
            'skus': skus,
            'page': 'user'
        }

        # 使用模板
        return render(request, 'df_user/user_center_info.html', context)


# /user/order
# class UserOrderView(View):
class UserOrderView(LoginRequiredMixin, View):
    """用户中心-订单页"""

    def get(self, request, page):
        """显示"""
        # 获取登录用户
        user = request.user
        # 获取用户的所有订单信息
        orders = OrderInfo.objects.filter(user=user)

        # 遍历获取每个订单对应的订单商品的信息
        for order in orders:
            # 获取订单商品的信息
            order_skus = OrderGoods.objects.filter(order=order)

            # 遍历order_skus计算订单中每件商品的小计
            for order_sku in order_skus:
                # 计算订单商品的小计
                amount = order_sku.price * order_sku.count

                # 给order_sku增加属性amount, 保存订单中每个商品的小计
                order_sku.amount = amount

            # 获取订单状态名称和计算订单实付款
            order.status_title = OrderInfo.ORDER_STATUS[order.order_status]
            order.total_pay = order.total_price + order.transit_price

            # 给order对象增加属性order_skus，包含订单中订单商品的信息
            order.order_skus = order_skus

        # 分页
        from django.core.paginator import Paginator
        # Paginator(被分页的信息, 每页显示信息条数)
        paginator = Paginator(orders, 3)

        # 处理页码
        page = int(page)

        # 对用户输入的页码数进行判断, 如果大于总页数则设置页码为1
        if page > paginator.num_pages:
            page = 1

        # 获取第page页的内容
        order_page = paginator.page(page)

        # 处理页码列表
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(num_pages - 2, num_pages + 3)

        # 组织上下文
        context = {
            'order_page': order_page,
            'pages': pages,
            'page': 'order'
        }

        # 使用模板
        return render(request, 'df_user/user_center_order.html', context)


# /user/address
# class AddressView(View):
class AddressView(LoginRequiredMixin, View):
    """用户中心-地址页"""

    def get(self, request):
        """显示"""
        address = Address.objects.get_default_address(user=request.user)
        content = {
            'address': address,
            'page': 'address'
        }

        return render(request, 'df_user/user_center_site.html', content)

    def post(self, request):
        """用户收货地址提交"""
        # 接收参数
        receiver = request.POST.get('receiver')
        addr = request.POST.get('recv_address')
        recv_code = request.POST.get('recv_code')
        phone = request.POST.get('phone')

        # 参数校验
        err_data_lose = {'errmsg': '数据不完整'}
        err_phone = {'errmsg': '号码格式错误'}
        if not all([receiver, addr, phone]):
            return render(request, 'df_user/user_center_site.html', err_data_lose)

        # 手机号码校验
        # phone_re = re.match(r"^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", phone)
        # if not phone_re:
        #     return render(request, 'df_order/user_center_site.html', err_phone)

        # 业务处理
        # 对默认地址进行判断
        user = request.user
        address = Address.objects.get_default_address(user)

        is_default = True
        if address is not None:
            is_default = False

        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=recv_code,
                               phone=phone,
                               is_default=is_default)

        # 返回应答
        return redirect(reverse('user:address'))
