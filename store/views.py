from django import forms, template
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.contrib import messages
from django.contrib.auth import authenticate , login , logout
import json
import datetime
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_text
from .tokens import account_activation_token
from .models import *
from .utils import cookieCart,cartData,guestOrder
from django.http import HttpResponse
from django.contrib.sites.shortcuts import get_current_site
# Create your views here.
from .forms import CreateUserForm

def registerPage(request):
    form = CreateUserForm

    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save() 
            username = form.cleaned_data.get('username')
            current_site = get_current_site(request)
            email_subject='Activate your Medbuy account'
            email_body=render_to_string('store/account_activation_email.html',{
                'user':username,
                'domain':current_site.domain,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)),
                'token':account_activation_token.make_token(user),
            })
            email_id = form.cleaned_data.get('email')
            email = EmailMessage(
                email_subject,
                email_body,
                'youremail@',
                [email_id],
                )
            email.send(fail_silently=False)
            Customer.objects.create(
                user=user,
                name = username,
                email = form.cleaned_data.get('email'),
            )

            
            messages.success(request,'Account was created for '+ username +'.Please confirm your email address to complete the registration')
            return redirect('login')

    context={'form':form}
    return render(request,'store/register.html',context)

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # return redirect('home')
        return redirect('store')
    else:
        return HttpResponse('Activation link is invalid!')


def loginPage(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username,password=password)

        if user is not None:
            login(request,user)
            return redirect('store')

    context={}
    return render(request,'store/login.html',context) 


def store(request):
    data = cartData(request)
    cartItems = data['cartItems']
    products = Product.objects.all()
    context={'products':products,'cartItems':cartItems}
    if request.method == 'POST':
        items = data['items']
        productId = request.POST.get('pid')
        product = Product.objects.get(id=productId)
        context={'product':product,'cartItems':cartItems,'items':items}
        return render(request,'store/product.html',context)

    return render(request,'store/store.html',context)

def search(request):
    if request.method == 'POST':
        productName = request.POST.get('search')
        data = cartData(request)
        cartItems = data['cartItems']
        products = Product.objects.all()    
        context={'products':products,'cartItems':cartItems,'productName':productName}
        return render(request,'store/search.html',context)

def cart(request):

    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items':items,'order':order,'cartItems':cartItems}
    return render(request, 'store/cart.html', context)

def orders(request):
    if request.user.is_authenticated:
        data = cartData(request)
        cartItems = data['cartItems']
        customer=request.user.customer
        orders = customer.order_set.all()
        items=[]
        for order in orders :
            if order.complete:
                item=order.orderitem_set.all()
                items.append(item)
        context ={'items':items,'cartItems':cartItems}
        return render(request,'store/orders.html',context)

def checkout(request):
    
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
    context = {'items':items,'order':order,'cartItems':cartItems}
    return render(request, 'store/checkout.html', context)

    
def log_out(request):
    if request.method == 'POST':
        logout(request)
        return redirect('store')


def updateitem(request):
    data= json.loads(request.body)
    productId= data['productId']
    action=data['action']
    print('Action:',action)
    print('Product:',productId)

    customer=request.user.customer
    product=Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer,complete=False)
    orderitem, created = OrderItem.objects.get_or_create(order=order,product=product)

    if action=='add':
        orderitem.quantity+=1
    elif action=='remove':
        orderitem.quantity-=1
    
    orderitem.save()

    if orderitem.quantity<=0:
        orderitem.delete()
    return JsonResponse('item was added',safe=False)

from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
@csrf_exempt    
def processOrder(request):
    transaction_id=datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer,complete=False)
        email_id = customer.email
        name = customer.name
    
    else:
        customer,order = guestOrder(request,data)
        email_id = data['form']['email']
        name = data['form']['name']
    
    total= float(data['form']['total'])
    order.transaction_id = transaction_id
    template =render_to_string('store/order_success_mail.html',{'name':name})

    if total == float(order.get_cart_total):
        order.complete = True
        
    order.save()
    if order.shipping == True:
        ShippingAddress.objects.create(
            customer = customer,
            order = order,
            address=data['shipping']['address'],
            city=data['shipping']['city'],
            state=data['shipping']['state'],
            pincode=data['shipping']['pincode'],
        )
    if order.complete:
        email_sub = 'Thanks for ordering at MedBuy!'
        email = EmailMessage(
                email_sub,
                template,
                'youremail@',
                [email_id],
                )
        email.send(fail_silently=True) 
    return JsonResponse('Payment complete!',safe= False)
