from cron import four11


def test_four11_user():
    student = four11.Four11User(
        id=1,
        firstname="John",
        preferred_name="Johnny",
        lastname="Doe",
        lunch_id=2,
        email="jdoe@eastsideprep.org",
        gradyear="2021",
        photo_url="https://four11.eastsideprep.org/epschedule/photos/1",
    )
    assert student.username() == "jdoe"
    assert student.display_name() == "Johnny Doe"
    assert student.is_student()
    assert not student.is_staff()
    assert student.class_of() == 2021

    teacher = four11.Four11User(
        id=2,
        firstname="Jane",
        lastname="Smith",
        lunch_id=3,
        email="jsmith@eastsideprep.org",
        gradyear="fac/staff",
        photo_url="https://four11.eastsideprep.org/epschedule/photos/2",
    )
    assert teacher.username() == "jsmith"
    assert teacher.display_name() == "Jane Smith"
    assert not teacher.is_student()
    assert teacher.is_staff()
    assert teacher.class_of() is None
