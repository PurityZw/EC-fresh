# 导入Celery类
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

# 初始化django运行所依赖的环境变量
# 这两行代码在启动worker一端打开
import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()

from df_goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

# 创建Celery类的对象
app = Celery('celery_tasks.tasks', broker='redis://172.16.26.130:6379/4')


# 封装任务函数
@app.task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = """
        <h1>%s, 欢迎您成为天天生鲜注册会员</h1>
        请点击一下链接激活您的账号(1小时之内有效)<br/>
        <a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>
    """ % (username, token, token)

    # 发送激活邮件
    # send_mail(subject='邮件标题',
    #           message='邮件正文',
    #           from_email='发件人',
    #           recipient_list='收件人列表')
    # 模拟send_mail发送邮件时间
    send_mail(subject, message, sender, receiver, html_message=html_message)


@app.task
def generate_static_index_html():
    """
    生成静态首页文件
    :return:
    """

    # 获取商品分类
    types = GoodsType.objects.all()

    # 获取商品展示类
    index_banner = IndexTypeGoodsBanner.objects.all().order_by('index')

    # 获取商品活动类, 根据index进行排序
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    for type in types:
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display=1)
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display=0)

        # 给type对象动态增加属性
        type.image_banner = image_banner
        type.title_banner = title_banner

    # 由于静态文件是未登录状态,设置购物车为0
    cart_count = 0

    # 使用模板
    from django.template import loader
    # 1.加载模板文件
    temp = loader.get_template('static_index.html')

    # 2.模板渲染
    static_temp = temp.render(temp)

    # 生成静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_temp)
