from django.db import models


class BaseModel(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_Delete = models.BooleanField(default=False, verbose_name_='删除标记')

    class Meta:
        # 指定这个类是抽象模型类
        abstract = True
