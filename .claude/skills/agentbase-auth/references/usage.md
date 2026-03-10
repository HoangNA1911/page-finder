# AgentBase Auth — Decorator Usage Examples

## Static API Key (`@requires_api_key` with M2M flow)

```python
from greennode_agentbase import requires_api_key

@requires_api_key(provider_name="openai-key", auth_flow="M2M")
def call_openai(api_key: str):
    # api_key is automatically injected from the stored provider
    client = openai.OpenAI(api_key=api_key)
    return client.chat.completions.create(...)
```

## Delegated API Key (`@requires_api_key` with USER_FEDERATION flow)

```python
from greennode_agentbase import requires_api_key

@requires_api_key(
    provider_name="user-openai-key",
    auth_flow="USER_FEDERATION",
    callback_url="https://myapp.com/callback",
    on_auth_url=lambda url: print(f"Please authorize: {url}"),
)
async def call_openai(api_key: str):
    # api_key is automatically injected after user completes delegation
    client = openai.OpenAI(api_key=api_key)
    return client.chat.completions.create(...)
```

## OAuth2 M2M Token (`@requires_access_token` with M2M flow)

```python
from greennode_agentbase import requires_access_token

@requires_access_token(
    provider_name="google-oauth",
    scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    auth_flow="M2M",
)
async def read_calendar(access_token: str):
    # access_token is automatically injected via client credentials flow
    pass
```

## OAuth2 3LO Token (`@requires_access_token` with USER_FEDERATION flow)

```python
from greennode_agentbase import requires_access_token

@requires_access_token(
    provider_name="google-oauth",
    scopes=["openid", "email"],
    auth_flow="USER_FEDERATION",
    callback_url="https://myapp.com/callback",
    on_auth_url=lambda url: print(f"Please authorize: {url}"),
)
async def get_user_info(access_token: str):
    # access_token injected after user completes OAuth consent
    pass
```
