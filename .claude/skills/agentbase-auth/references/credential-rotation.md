# Credential Rotation

To rotate credentials stored in auth providers, use the update operations.

## Rotating a Static API Key

When an external API key needs to be rotated (e.g., OpenAI key renewal, compromised key):

1. Generate the new key from the external service (e.g., OpenAI dashboard)
2. Update the stored key using `apikey update`:
   ```bash
   curl -X PUT "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers/openai-key" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"apikey": "sk-new-..."}'
   ```
3. The agent will immediately use the new key on subsequent requests — no redeployment needed

## Rotating OAuth2 Client Credentials

When OAuth2 client credentials need rotation:

1. Generate new credentials from the OAuth2 provider (e.g., Google Cloud Console)
2. Update the provider using `oauth2 update`:
   ```bash
   curl -X PUT "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/oauth2-providers/google-oauth" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "clientId": "new-xxx.apps.googleusercontent.com",
       "clientSecret": "GOCSPX-new-xxx",
       "authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth",
       "tokenUrl": "https://oauth2.googleapis.com/token"
     }'
   ```
3. Existing user authorizations may need to be re-established depending on the OAuth2 provider

## Rotating Delegated API Keys

Delegated providers have no stored credentials to rotate — end-users manage their own keys. To force users to re-authorize, delete and recreate the delegated provider.

## Rotating Platform IAM Credentials

To rotate the IAM service account credentials used for platform API access:

1. Go to https://iam.console.vngcloud.vn/service-accounts
2. Click your service account → **"Security credentials"** tab → **"Reset"**
3. **Warning**: The old secret is invalidated immediately — update all systems using it
4. Update `GREENNODE_CLIENT_ID`/`GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json`
5. For deployed runtimes, use `PATCH /agent-runtimes/{id}/reset-service-account` (see `/agentbase-runtime`) to regenerate the runtime's auto-managed credentials
