from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

# 初始化django运行所依赖的环境变量
# 这两行代码在启动worker一端打开
# import os
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")

# 使用Celery创建对象 Celery(第一个参数是名字,)
app = Celery('celery_task', broker='redis://172.16.26.130:6379/0')


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
