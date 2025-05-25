from ninja import NinjaAPI, Schema
from typing import List
from .models import Todo, ApiKey
from django.shortcuts import get_object_or_404
from datetime import date
from ninja.security import APIKeyHeader
import uuid
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from datetime import datetime


class MyApiKeyAuth(APIKeyHeader):
    param_name = "Api-Key"
    header = "Authorization"

    def authenticate(self, request, key):
        try:
            api_key = ApiKey.objects.select_related('user').get(key=key)
            return api_key.user
        except ApiKey.DoesNotExist:
            return None

api = NinjaAPI(auth=[MyApiKeyAuth()])

class TodoSchema(Schema):
    id: int
    title: str
    completed: bool
    due_date: date | None

#7 session (5/21) : 과제
class CheckUser(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    date_joined: datetime | None
    api_key: str

class UserProfileUpdateSchema(Schema):
   email: str=None
   first_name: str=None
   last_name: str=None

class NewApiKeySchema(Schema):
    api_key: uuid.UUID

class LoginIn(Schema):
    username: str
    password: str

class ApiKeyOut(Schema):
    api_key: uuid.UUID

@api.get("/todos", response=List[TodoSchema])
def list_todos(request):
    todos = Todo.objects.filter(owner=request.auth).all()
    return todos

@api.get("/todos/{todo_id}", response=TodoSchema)
def get_todo(request, todo_id: int):
    todo = get_object_or_404(Todo, id=todo_id, owner=request.auth)
    return todo

@api.post("/todos", response=TodoSchema)
def create_todo(request, todo_in: TodoSchema):
    todo = Todo.objects.create(**todo_in.dict(), owner=request.auth)
    return todo

@api.put("/todos/{todo_id}", response=TodoSchema)
def update_todo(request, todo_id: int, todo_in: TodoSchema):
    todo = get_object_or_404(Todo, id=todo_id, owner=request.auth)
    for key, value in todo_in.dict().items():
        setattr(todo, key, value)
    todo.save()
    return todo

@api.delete("/todos/{todo_id}")
def delete_todo(request, todo_id: int):
    todo = get_object_or_404(Todo, id=todo_id, owner=request.auth)
    todo.delete()

@api.post("/token", response=ApiKeyOut, auth=None)
def generate_token(request, user_login: LoginIn):
    user = authenticate(
        request,
        username=user_login.username,
        password=user_login.password
    )
    if user:
        api_key, created = ApiKey.objects.get_or_create(user=user)
        return ApiKeyOut(api_key=api_key.key)
    else:
        from ninja.errors import HttpError
        raise HttpError(status_code=401, message="Invalid username or password")

#7 session (5/21) : 과제
@api.get("/me", response=CheckUser)
def get_current_user(request):
    user = request.auth  
    try:
        api_key = ApiKey.objects.get(user=user)
    except ApiKey.DoesNotExist:
        api_key = None

    return CheckUser(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        date_joined=user.date_joined if hasattr(user, "date_joined") else None,
        api_key=str(api_key.key) if api_key else ""
    )

@api.put("/me", response=CheckUser)
def update_current_user(request, data: UserProfileUpdateSchema):
    user = request.auth
    for attr, value in data.dict(exclude_unset=True).items():
        setattr(user, attr, value)
    user.save()
    try:
        api_key = ApiKey.objects.get(user=user)
    except ApiKey.DoesNotExist:
        api_key = None
    return CheckUser(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        date_joined=user.date_joined,
        api_key=str(api_key.key) if api_key else ""
    )

@api.post("/me/regenerate-key", response=NewApiKeySchema)
def regenerate_api_key(request):
    user = request.auth
    api_key = ApiKey.objects.get(user=user)
    api_key.key = uuid.uuid4()
    api_key.save()
    return NewApiKeySchema(api_key=api_key.key)