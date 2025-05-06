from django.shortcuts import render, redirect
from django.contrib.auth import login

from usuarios.forms import CustomAuthenticationForm




def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
        else:
            print("Errores del formulario de login:")
            print(form.errors)
    else:
        form = CustomAuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})
