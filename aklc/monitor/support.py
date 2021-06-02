from .models import (
    Profile,
    webNotification,
)
from django.contrib.auth.models import User

from django import template

# ******************************************************************
def sendNotification(recipients, context, inEmail=True, inSubject="", inTemplate="", inNode=None):
    """
    """

    try:
        t = template.loader.get_template(inTemplate)
        body = t.render(context)
    except Exception as e:
        print(
            f"sendNotification error {e} processing template: {template}"
        )
        return

    for r in recipients:
        if inEmail and r.email:
            nContext = context
            nContext["person"] = r
            cBody = t.render(nContext)
            wn = webNotification(
                address=r.email,
                subject=inSubject,
                body=cBody,
                email=True,
                user=r,
            )
            if inNode:
                wn.node = inNode
            wn.save()