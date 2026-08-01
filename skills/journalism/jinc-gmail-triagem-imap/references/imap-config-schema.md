# Estrutura do `imap-config.json`

Arquivo em: `/opt/data/journali/imap-config.json`

Campos:
- `host` (string): host IMAP. Ex.: `imap.gmail.com`
- `port` (number): porta IMAP SSL. Ex.: `993`
- `username` (string): email da conta (Workspace)
- `password` (string): preferir **App Password** (ou segredo usado no IMAP)
- `search_folder` (string, opcional): pasta padrão. Ex.: `INBOX`

Exemplo:
```json
{
  "host": "imap.gmail.com",
  "port": 993,
  "username": "jornalistainclusivo@gmail.com",
  "password": "SENHA_OU_APP_PASSWORD",
  "search_folder": "INBOX"
}
```

## Notas de segurança
- Não versionar o arquivo.
- Evitar colar senhas em logs.
- Se houver falha, validar: `host`, `port`, autenticação e se a conta permite acesso IMAP.