from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

# 使用Celery创建对象 Celery(第一个参数是名字,)
app = Celery('celery_task', broker='redis://172.16.26.130/0')


# 要想使封装的函数为celery函数需要用对象的task方法进行装饰
@app.task
def send_register_activate_email(toemail, username, token):
    # 发送激活邮件
    # send_mail(subject='邮件标题',
    #           message='邮件正文',
    #           from_email='发件人',
    #           recipient_list='收件人列表')

    subject = '天天生鲜激活邮件'
    message = """
        <h1>%s,请点击该链接进行激活(有效时间5分钟)</h1>
        <a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>
    """ % (username, token, token)
    from_email = settings.EMAIL_FROM
    receiver = [toemail]
    send_mail(subject, message, from_email, receiver, html_message=message)
