# Migracao para Neon como banco principal

Este projeto deve usar o Neon como banco oficial de producao. O Postgres local
fica apenas para desenvolvimento ou testes descartaveis.

## 1. Configurar a URL do Neon

Use a connection string direta do Neon para migracao. Evite a URL com
`-pooler` em comandos de migracao.

```powershell
$env:NEON_DATABASE_URL="postgresql://neondb_owner:npg_GfTjZ3CpS0Hy@ep-lively-water-acsdt1ns.sa-east-1.aws.neon.tech/neondb?sslmode=require"
```

No Streamlit Cloud, configure o mesmo valor em Secrets como:

```toml
NEON_DATABASE_URL="postgresql://usuario:senha@ep-....neon.tech/dbname?sslmode=require"
```

## 2. Conferir contagens sem alterar o Neon

```powershell
$env:NEON_DATABASE_URL="postgresql://neondb_owner:npg_GfTjZ3CpS0Hy@ep-lively-water-acsdt1ns.sa-east-1.aws.neon.tech/neondb?sslmode=require"
.\.venv\Scripts\python.exe scripts\migrate_local_to_neon.py
```

O script mostra quantas linhas existem no Postgres local e no Neon.

## 3. Migrar os dados locais para o Neon

Este comando substitui os dados das tabelas do dashboard no Neon pelos dados do
Postgres local:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_local_to_neon.py --yes --replace-neon-tables
```

Tabelas migradas:

- `public.base_historica_manutencao`
- `public.servicos_executados`

O script tambem ajusta a sequence `base_historica_manutencao_id_seq` depois da
copia.

## 4. Rodar o app apontando para o Neon

Local:

```powershell
$env:NEON_DATABASE_URL="postgresql://neondb_owner:npg_GfTjZ3CpS0Hy@ep-lively-water-acsdt1ns.sa-east-1.aws.neon.tech/neondb?sslmode=require"
streamlit run Python/app.py
```

Docker Compose:

```powershell
$env:NEON_DATABASE_URL="postgresql://neondb_owner:npg_GfTjZ3CpS0Hy@ep-lively-water-acsdt1ns.sa-east-1.aws.neon.tech/neondb?sslmode=require"
docker compose -f Docker/docker-compose.yml up -d --build app
```

## 5. Indicador visual no app

O menu lateral mostra um badge logo abaixo do logo:

- `Neon ativo`: host contem `neon.tech`
- `Banco local`: `localhost`, `127.0.0.1`, `postgres` ou `host.docker.internal`
- `Banco remoto`: outro host PostgreSQL

Assim fica claro onde os dados serao lidos e gravados antes de usar a tela de
entrada de dados.

## Referencias Neon

- https://neon.com/docs/get-started-with-neon/connect-neon
- https://neon.com/docs/import/migrate-intro
- https://neon.com/docs/connect/connection-pooling
