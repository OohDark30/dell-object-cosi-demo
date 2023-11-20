from inflection import parameterize
from flask import g
from markupsafe import Markup


def slugify(myvar):
    return parameterize(myvar)[:80].rstrip('-')

#This data would better go in a database...
errorDict = { 
    "Err1": "ERROR 1: watch out for error n.1!",
    "Err2": "ERROR 2: watch out for error n.2!",
    "Err9": "ERROR 9: watch out for error n.9!"
}


def displayError(errNum):
    key = "Err"+str(errNum)
    result = errorDict[key]
    return result


msgDict = { 
    "Msg1": "<p>This is a <b>nice</b> message, the first of the list</p>",
    "Msg2": "<p>This is an even <b>nicer</b> message.</p>",
    "Msg3": "<p>The name of the COSI K8S Secret must be entered.</p>",
    "Msg4": "<p>The specified COSI K8S Secret file doesn't exist.</p>"
}


def displayMessage(msgKey):
    #THE DECORATOR IS NEEDED TO DISABLE CACHING OF JINJA CALLS!!!
    result = Markup(msgDict[msgKey])
    return result
