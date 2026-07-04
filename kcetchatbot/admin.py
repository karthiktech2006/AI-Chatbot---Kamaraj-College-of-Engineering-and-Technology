from django.contrib import admin
from .models import ChatLead, CallRequest

@admin.register(ChatLead)
class ChatLeadAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "mobile", "created_at"]
    search_fields = ["name", "mobile"]
    list_filter = ["created_at"]


@admin.register(CallRequest)
class CallRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "mobile", "created_at"]
    search_fields = ["name", "mobile"]
    list_filter = ["created_at"]