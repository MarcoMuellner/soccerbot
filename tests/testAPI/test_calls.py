import pytest
from api.calls import *
from database.models import *
from httmock import urlmatch, HTTMock

@urlmatch(netloc=r'(.*\.)?google\.com$')
def google_mock(url, request):
    return 'Feeling lucky, punk?'

with HTTMock(google_mock):
    r = requests.get('http://google.com/')
    print(r.content)  # 'Feeling lucky, punk?'


def testAPICallObjects():
    """
    Checking API keywords.
    """
    for key,values in ApiCalls.__dict__.items():
        if key == "api_home" or key.startswith("__"):
            continue
        with pytest.raises(ValueError):
            int(values) #simple check, should raise ValueError if it is really a string

        assert values[-1] != "/" # no backslash at end!