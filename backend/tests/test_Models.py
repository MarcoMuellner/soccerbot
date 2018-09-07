from ..obj.models import *
import pytest
import time

modelList = [Federation,Competition,Season,Country,Stage,Team,Player,Calendar,SeasonStats,PlayerStats,TeamStats]

@pytest.mark.django_db
@pytest.mark.parametrize("model",modelList)
def testModelUpdateData(model):
    now = time.clock()
    model.updateData()
    later = time.clock()
    print(f"{model} took {later-now}")

    #assert len(model.objects.all()) > 0

