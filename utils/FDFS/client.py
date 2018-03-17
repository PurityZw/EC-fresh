from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    """建立自定义文件存储类"""

    def __init__(self, client_conf=None, nginx_url=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF

        self.client_conf = client_conf

        if nginx_url is None:
            nginx_url = settings.FDFS_NGINX_URL

        self.nginx_url = nginx_url

    def _save(self, name, content):
        """
        文件存储处理

        :param name:存储的文件的名
        :param content:存储文件的内容
        """

        client = Fdfs_client(self.client_conf)

        # 获取上传内容
        file_content = content.read()

        response = client.upload_by_buffer(file_content)

        if response is None or response.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('上传文件到fast dfs系统失败')

        # 获取保存文件id
        file_id = response.get('Remote file_id')

        # 返回file_id
        return file_id

    def exists(self, name):
        """判断文件是否存在"""
        # 设置False是为了使FDFS服务器每次都可以生成不同的ID
        return False

    def url(self, name):
        """返回可访问的url地址"""
        return self.nginx_url + name
