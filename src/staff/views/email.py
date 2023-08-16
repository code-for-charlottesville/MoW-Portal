from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.core import mail
from django.core.mail import EmailMessage
from django.core.mail import send_mail as sm
from django.shortcuts import HttpResponse, render
from django.contrib.auth.forms import PasswordResetForm

log = getLogger(__name__)


def send_email(subject, message, recipient_list):
    res = sm(
        subject=subject,
        message=message,
        from_email="mow.charlottesville@gmail.com",
        recipient_list=recipient_list,
        fail_silently=False,
    )

    return res


def reset_password(email, request):
    """
    Reset the password for all (active) users with given E-Mail adress
    """
    subject_template = 'registration/welcome_email_subject.html'
    template = 'registration/welcome_email.html'
    from_email = "mow.charlottesville@gmail.com"
    form = PasswordResetForm({'email': email})

    if form.is_valid():
        form.save(
            from_email=from_email,
            subject_template_name=subject_template,
            email_template_name=template,
            html_email_template_name=template,
            request=request
        )
