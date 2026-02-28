from django.contrib import admin
from .models import Level, Question, UserProgress

# เอาตารางของเราไปโชว์ในหน้า Admin
admin.site.register(Level)
admin.site.register(Question)
admin.site.register(UserProgress)