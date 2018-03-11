from django.shortcuts import render
from django.views.generic import View

# Create your views here.
class IndexView(View):
    def get(self, request):
        return render(request, 'df_goods/index.html')