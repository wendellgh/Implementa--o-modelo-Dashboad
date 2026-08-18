# Migração entre PostgreSQL local e Neon

## Segurança primeiro

Nunca grave connection strings, senhas ou tokens neste repositório. Use o
Neon Console e o secret store da hospedagem em produção; para desenvolvimento
local, use um arquivo `.env`, que é ignorado pelo Git.

A credencial que já apareceu no histórico deve ser considerada comprometida.
Removê-la dos arquivos atuais não revoga o acesso e não a remove dos commits
antigos.

## Rotação da credencial exposta

Faça a rotação de forma coordenada para não interromper o dashboard:

1. No Neon Console, crie uma nova role com os privilégios mínimos necessários.
   Se isso não for possível, redefina a senha da role atual e atualize os
   consumidores imediatamente.
2. Obtenha duas connection strings para a nova role:
   - pooled, para o dashboard/Streamlit (`DATABASE_URL`);
   - direta, para os scripts de migração (`NEON_DATABASE_URL`).
3. No painel de Secrets do Streamlit Cloud ou da hospedagem, atualize
   `DATABASE_URL` e gere também um novo `DASHBOARD_AUTH_SECRET` aleatório e
   forte.
4. Reinicie/republique a aplicação e valide a conexão usando o indicador de
   banco exibido no dashboard.
5. Atualize o `.env` apenas nas máquinas autorizadas e valide os scripts em
   modo de prévia.
6. Revogue a role/senha antiga depois que todos os consumidores estiverem
   usando a nova credencial.

O secret store do Streamlit tem precedência sobre as variáveis de ambiente no
dashboard. Atualize ou remova também qualquer valor antigo existente nele.

## Configuração local

Crie o arquivo local a partir do modelo:

```powershell
Copy-Item .env.example .env
```

Preencha no `.env`, sem versioná-lo:

```dotenv
DATABASE_URL=<connection-string-pooled-do-Neon>
NEON_DATABASE_URL=<connection-string-direta-do-Neon>
LOCAL_DATABASE_URL=<connection-string-do-PostgreSQL-local>
DASHBOARD_AUTH_SECRET=<segredo-aleatorio-forte>
```

Os scripts carregam o `.env` automaticamente sem substituir variáveis já
definidas no processo. A precedência é:

1. argumento `--neon-url`;
2. `NEON_DATABASE_URL`;
3. `DATABASE_URL`.

## Acrescentar somente linhas ausentes

Prévia, sem inserir dados nem alterar schema/sequências:

```powershell
python scripts\append_missing_local_to_neon.py
```

Depois de conferir as contagens, execute explicitamente:

```powershell
python scripts\append_missing_local_to_neon.py --adicionar-dados
```

Esse fluxo preserva as linhas existentes no Neon e acrescenta apenas as linhas
que faltam segundo as colunas de comparação do script.

Tabelas processadas:

- `public.base_historica_manutencao`;
- `public.servicos_executados`.

Ao final de uma execução real, a sequência
`base_historica_manutencao_id_seq` é sincronizada.

## Substituir as tabelas do Neon

Prévia das contagens:

```powershell
python scripts\migrate_local_to_neon.py
```

A execução abaixo trunca as tabelas de destino antes da cópia. Use somente
quando a substituição integral for realmente desejada:

```powershell
python scripts\migrate_local_to_neon.py --executar --substituir-tabelas-neon
```

## Espelhar o Neon no PostgreSQL local

Prévia das contagens:

```powershell
python scripts\neon_to_local.py
```

A execução abaixo trunca as tabelas locais antes da cópia:

```powershell
python scripts\neon_to_local.py --executar --substituir-tabelas-local
```

Para escolher outro banco local, informe uma URL sem gravá-la no repositório:

```powershell
python scripts\neon_to_local.py --local-url $env:LOCAL_DATABASE_URL
```

## Executar o dashboard

Com `DATABASE_URL` configurada no ambiente ou no secret store:

```powershell
streamlit run Python/app.py
```

Com Docker Compose:

```powershell
docker compose -f Docker/docker-compose.yml up -d --build app
```

O menu lateral identifica o destino ativo:

- `Neon ativo`: host do Neon;
- `Banco local`: PostgreSQL local ou container local;
- `Banco remoto`: outro host PostgreSQL.

## Limpeza do histórico Git

Depois da rotação, planeje a remoção do segredo do histórico com
`git filter-repo` em um clone dedicado. Essa operação altera os hashes dos
commits e exige force-push coordenado, atualização de PRs e reclone dos
checkouts. Não execute a reescrita no checkout de trabalho com arquivos locais
modificados. Cópias, forks e caches antigos devem continuar sendo tratados como
potencialmente comprometidos mesmo após a reescrita.

## Referências oficiais

- <https://neon.com/docs/get-started-with-neon/connect-neon>
- <https://neon.com/docs/import/migrate-intro>
- <https://neon.com/docs/connect/connection-pooling>
