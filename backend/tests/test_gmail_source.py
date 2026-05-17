from app.services.ingestion.real_gmail_source import RealGmailSource


class FakeListCall:
    def __init__(self, captured):
        self.captured = captured

    def execute(self):
        return {"messages": []}


class FakeMessages:
    def __init__(self):
        self.queries = []

    def list(self, **kwargs):
        self.queries.append(kwargs["q"])
        return FakeListCall(self.queries)


class FakeUsers:
    def __init__(self, messages):
        self.messages_obj = messages

    def messages(self):
        return self.messages_obj


class FakeService:
    def __init__(self):
        self.messages_obj = FakeMessages()

    def users(self):
        return FakeUsers(self.messages_obj)


def test_gmail_query_includes_label_when_required(monkeypatch):
    monkeypatch.setenv("EMAIL_REQUIRE_LABEL", "true")
    monkeypatch.setenv("EMAIL_GMAIL_LABEL", "EverCurrent/Warehouse-Robot-V2")
    monkeypatch.setenv("EMAIL_INCLUDE_SENT", "false")

    source = RealGmailSource()
    service = FakeService()
    source._fetch_query(service, "in:inbox", "received")

    assert service.messages_obj.queries == [
        'in:inbox newer_than:14d label:"EverCurrent/Warehouse-Robot-V2"'
    ]


def test_gmail_query_omits_label_by_default(monkeypatch):
    monkeypatch.delenv("EMAIL_REQUIRE_LABEL", raising=False)

    source = RealGmailSource()
    service = FakeService()
    source._fetch_query(service, "in:inbox", "received")

    assert service.messages_obj.queries == ["in:inbox newer_than:14d"]
