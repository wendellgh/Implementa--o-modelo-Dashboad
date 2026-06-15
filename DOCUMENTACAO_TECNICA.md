# Documentação Técnica — Dashboard de Manutenção (Streamlit + PostgreSQL)

## 1) Visão geral

Este repositório implementa um dashboard em **Streamlit** para monitoramento de indicadores de manutenção por equipamento, usando dados vindos de um banco **PostgreSQL**.

A aplicação principal:
- configura a página;
- consulta duas visões SQL (`vw_dashboard_resumo` e `vw_dashboard_evolucao_mensal`);
- calcula KPIs globais;
- permite filtro por equipamento;
- renderiza gráficos e tabela.

Arquivos centrais:
- `Python/app.py`: ponto de entrada da aplicação.
- `Python/dashboard/*.py`: módulos de configuração, acesso a dados, regras de negócio e visualização.
- `Docker/docker-compose.yml`: infraestrutura local de Streamlit + PostgreSQL + pgAdmin.
- `Docker/Dockerfile`: imagem Docker da aplicação Streamlit.
- `importacaoCSV.py`: script de carga em lote de CSV para tabela histórica.

---

## 2) Estrutura do projeto

```text
.
├── Basehistorica.csv
├── Docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── importacaoCSV.py
├── Python/
│   ├── app.py
│   ├── requirements.txt
│   └── dashboard/
│       ├── __init__.py
│       ├── config.py
│       ├── data.py
│       ├── database.py
│       ├── filters.py
│       ├── metrics.py
│       ├── tables.py
│       └── visualizations.py
└── README
```

---

## 3) Fluxo de execução da aplicação

### 3.1 Entrada (`Python/app.py`)

A função `main()` executa a sequência:
1. `st.set_page_config(**PAGE_CONFIG)` para layout/título da página.
2. `st.title(APP_TITLE)` para o cabeçalho.
3. tentativa de carregar os dois DataFrames via `carregar_dados()`.
4. tratamento de erro com `st.error(...)` + `st.stop()` se falhar conexão/consulta.
5. se `df_resumo` vier vazio, exibe aviso e para execução.
6. cálculo dos KPIs (`calcular_kpis`) e renderização (`render_kpis`).
7. aplicação de filtro por equipamento (`aplicar_filtro_equipamento`).
8. renderização de gráficos de resumo e evolução.
9. renderização da tabela final.

### 3.2 Camadas lógicas

O desenho atual pode ser entendido em camadas:
- **Configuração** (`config.py`): parâmetros estáticos (DB, queries, título, layout).
- **Infra de banco** (`database.py`): criação do `Engine` SQLAlchemy.
- **Acesso a dados** (`data.py`): leitura SQL e transformação mínima de datas.
- **Domínio/KPIs** (`metrics.py`): regras de cálculo.
- **Interação/filtro** (`filters.py`): widget Streamlit e recorte de DataFrames.
- **Apresentação** (`visualizations.py` e `tables.py`): gráficos e tabela.

---

## 4) Detalhamento por módulo

## 4.1 `dashboard/config.py`

Centraliza constantes do app:
- `PAGE_CONFIG`: título do browser e layout (`wide`).
- `APP_TITLE`: título exibido no dashboard.
- `DB_SETTINGS`: credenciais e endpoint de conexão (`app_user/app123@localhost:5432/app_db`).
- `RESUMO_QUERY`: `select * from vw_dashboard_resumo order by equipamento`.
- `EVOLUCAO_QUERY`: `select * from vw_dashboard_evolucao_mensal order by mes, equipamento`.

**Impacto:** mudanças aqui afetam toda a aplicação (ex.: troca de banco, renomear views, etc.).

## 4.2 `dashboard/database.py`

- Constrói uma URL SQLAlchemy no formato `postgresql+psycopg2://...`.
- Usa `@st.cache_resource` para manter o objeto `Engine` em cache entre reruns do Streamlit.

**Benefício:** evita recriar conexão a cada interação do usuário, reduzindo overhead.

## 4.3 `dashboard/data.py`

Tem três funções:
- `carregar_resumo()`: executa `RESUMO_QUERY`.
- `carregar_evolucao()`: executa `EVOLUCAO_QUERY` e converte coluna `mes` para datetime.
- `carregar_dados()`: retorna tupla `(df_resumo, df_evolucao)`.

`@st.cache_data` é usado nas leituras para evitar reconsulta desnecessária.

## 4.4 `dashboard/metrics.py`

### `calcular_kpis(df_resumo, df_evolucao_mensal)`
Calcula:
- `entrada_media_mensal`: média mensal de `total_qtd` a partir de `df_evolucao_mensal`;
- `total_qtd`: soma de `total_qtd`;
- `total_frota`: soma de `total_frota`;
- `percentual_geral`: `(total_qtd / total_frota) * 100`, com proteção de divisão por zero.

### `render_kpis(kpis)`
Renderiza 5 cards (colunas Streamlit), formatando:
- percentuais com 2 casas;
- totais inteiros com separador de milhar.

## 4.5 `dashboard/filters.py`

- Monta lista de equipamentos com opção inicial `Todos`.
- Exibe `st.selectbox("Filtrar equipamento", ...)`.
- Se `Todos`, retorna cópia dos DataFrames originais.
- Caso contrário, filtra ambos os DataFrames pela coluna `equipamento`.

## 4.6 `dashboard/visualizations.py`

Renderiza 3 gráficos Plotly:
1. **Barras agrupadas** de `total_qtd` vs `total_frota` por `equipamento`.
2. **Barras de percentual** (`percentual_recalculado`) por `equipamento` com texto no topo.
3. **Linha temporal** da evolução mensal (`percentual_qtd_x_frota`) por `mes` e `equipamento`.

Se o DataFrame de evolução estiver vazio, mostra `st.info(...)` e não tenta plotar.

## 4.7 `dashboard/tables.py`

- Exibe subtítulo e `st.dataframe` com os dados filtrados de resumo.

---

## 5) Dependências e infraestrutura

## 5.1 Dependências Python

Definidas em `Python/requirements.txt`:
- `streamlit`
- `pandas`
- `plotly`
- `sqlalchemy`
- `psycopg2-binary`

## 5.2 Docker Compose

`Docker/docker-compose.yml` sobe:
- **Streamlit** (`streamlit_app`) em `localhost:8501`.
- **PostgreSQL 16** (`postgres_app`) em `localhost:5432`.
- **pgAdmin 4** (`pgadmin_app`) em `localhost:8080`.

Com volume nomeado `postgres_data` para persistência. O projeto Compose mantém o nome interno `dados_docker` para reaproveitar containers/volumes existentes após a renomeação da pasta.

---

## 6) Modelo de dados esperado pelo dashboard

A aplicação não lê diretamente uma tabela bruta; ela depende de **duas views já prontas** no banco:
- `vw_dashboard_resumo`
- `vw_dashboard_evolucao_mensal`

Pelos usos no código, o dashboard espera pelo menos:

### Para `vw_dashboard_resumo`
- `equipamento`
- `total_qtd`
- `total_frota`
- `media_percentual`
- `percentual_recalculado`

### Para `vw_dashboard_evolucao_mensal`
- `mes`
- `equipamento`
- `percentual_qtd_x_frota`

Se qualquer coluna faltar ou tiver nome diferente, haverá erro em cálculo ou visualização.

---

## 7) Script de importação (`importacaoCSV.py`)

Esse script é um pipeline de carga histórica de CSV para PostgreSQL.

Etapas:
1. conecta no banco via SQLAlchemy;
2. lê CSV em lotes (`chunksize=5000`);
3. renomeia colunas do arquivo para padrão técnico;
4. converte data Excel serial (`origin="1899-12-30"`) para data;
5. normaliza percentual removendo `%` e trocando vírgula por ponto;
6. converte `frota` e `qtd` para inteiro;
7. faz `strip` em campos textuais;
8. no modo de acrescentar, compara cada chunk com as linhas já existentes no banco e grava somente as linhas ausentes com `to_sql(..., if_exists="append")`.

**Observação importante:** o caminho de arquivo CSV está hardcoded para Windows (`d:\Code\...`). Para uso em outros ambientes, substitua por caminho relativo/variável de ambiente.

---

## 7.1) Carga complementar de `servicos_executados`

A tabela `servicos_executados` pode receber dados de duas origens:
- Oracle, via `Python/Oracle/servicos_executados_pipeline.py`;
- CSV antigo `Importacoes/bsa_serv_exce.csv`, via `Importacoes/importa_servicos_executados.py`.

As duas origens passam pela normalização comum em `Python/dashboard/servicos_executados_schema.py`. Isso garante que, independentemente do cabeçalho original, o banco receba sempre o mesmo contrato de colunas:

```text
DATA
DATA_COMPETENCIA
ID_CONTRATO
CONTRATO
ID_EQUIPAMENTO
EQUIPAMENTO
ID_OPERADORA
OPERADORA
ID_SERVICO_EXECUTADO
SERVIC_EXECUTADO
QTD_SERVICO
```

### Fluxo recomendado

Use o Oracle para carregar os períodos/serviços disponíveis nessa origem. Depois use o CSV antigo para complementar períodos ou serviços que não existam no Oracle.

Na tela **Dados da Manutenção - Oracle**, o campo **Modo de carga no banco** oferece três comportamentos:
- `Acrescentar somente ausentes`: compara o CSV com o banco e insere apenas registros que ainda não existem. É o modo recomendado para complementar meses novos, por exemplo adicionar Maio quando o banco já tem dados até Abril.
- `Substituir periodos do CSV`: remove apenas os períodos presentes no CSV gerado e insere esses períodos novamente. Use quando quiser recarregar/corrigir meses específicos.
- `Substituir toda a tabela servicos_executados`: limpa toda a tabela antes da carga. Use apenas quando a intenção for reconstruir a tabela inteira.

Na mesma tela, a seção **Importar CSV externo** facilita a carga de dados que vêm de fora do Oracle. Ela permite:
- enviar um CSV pelo navegador;
- ou, se nenhum arquivo for enviado, carregar o arquivo padrão `Importacoes/bsa_serv_exce.csv`.

O botão **Carregar CSV externo no banco** usa o mesmo **Modo de carga no banco** selecionado acima.

A seção **Teste: importar Basehistorica.csv** permite carregar dados de teste para a tabela `base_historica_manutencao`. Ela também aceita upload pelo navegador ou usa o arquivo padrão `Importacoes/Basehistorica.csv`.

Essa carga tem modo próprio:
- `Acrescentar somente ausentes da Basehistorica`: compara o CSV com o banco e insere apenas registros que ainda não existem;
- `Substituir periodos da Basehistorica`: remove apenas os períodos presentes no CSV e insere esses períodos novamente;
- `Substituir toda a tabela base_historica_manutencao`: limpa toda a tabela histórica antes da carga.

Para importar o CSV antigo acrescentando somente o que ainda não existe no banco:

```powershell
python Importacoes\importa_servicos_executados.py
```

Esse modo compara o CSV com a tabela e insere somente as linhas ausentes. Os demais períodos, inclusive os carregados pelo Oracle, são preservados.

Para deixar essa intenção explícita, use o parâmetro em português:

```powershell
python Importacoes\importa_servicos_executados.py --adicionar-dados
```

O parâmetro antigo `--append` continua funcionando como apelido.

Para substituir somente os meses presentes no CSV:

```powershell
python Importacoes\importa_servicos_executados.py --replace-periods
```

Para limpar toda a tabela e recarregar somente pelo CSV antigo:

```powershell
python Importacoes\importa_servicos_executados.py --replace-table
```

Use `--replace-table` apenas quando a intenção for substituir completamente a tabela `servicos_executados`.

Para sincronizar do Postgres local para o Neon sem apagar dados já existentes no Neon:

```powershell
python scripts\append_missing_local_to_neon.py --adicionar-dados
```

Esse script compara as tabelas entre os bancos e insere somente as linhas ausentes no Neon.

Para substituir completamente as tabelas do Neon pelos dados locais:

```powershell
python scripts\migrate_local_to_neon.py --executar --substituir-tabelas-neon
```

Para substituir completamente o banco local pelo Neon:

```powershell
python scripts\neon_to_local.py --executar --substituir-tabelas-local
```

---

## 8) Pontos fortes atuais

- Código modular e legível, com separação por responsabilidade.
- Uso apropriado de cache do Streamlit (`cache_data` e `cache_resource`).
- Tratamento básico de erro no carregamento inicial.
- Visualizações objetivas para acompanhamento operacional.

---

## 9) Limitações e melhorias recomendadas

1. **Credenciais em código-fonte**
   - mover `DB_SETTINGS` para variáveis de ambiente (`.env`) e `st.secrets`.

2. **Dependência rígida de nomes de colunas/views**
   - validar schema na inicialização e mostrar mensagem orientativa.

3. **Qualidade de dados**
   - incluir validações (nulos, tipos esperados, intervalos) antes de calcular KPIs.

4. **Filtro único**
   - expandir para filtros por período, contrato e operadora.

5. **Observabilidade**
   - adicionar logging estruturado para falhas de conexão e consultas lentas.

6. **Script de importação não portátil**
   - parametrizar caminho, encoding e tabela por CLI/ENV.

---

## 10) Como executar localmente (resumo rápido)

1. Subir banco e aplicação:
```bash
docker compose -f Docker/docker-compose.yml up -d --build
```

2. Acessar o app:
```text
http://localhost:8501
```

---

## 11) Checklist para evoluir sem quebrar o dashboard

Quando alterar consultas ou schema do banco:
- [ ] manter nomes de colunas usados em `metrics.py`, `filters.py` e `visualizations.py`;
- [ ] garantir que `mes` continue parseável para datetime;
- [ ] validar se os gráficos aceitam os novos tipos de dados;
- [ ] revisar se KPI global continua fazendo sentido com o novo modelo;
- [ ] limpar cache do Streamlit após mudanças estruturais.

Quando alterar UI:
- [ ] preservar fluxo: KPI → filtro → gráficos → tabela;
- [ ] tratar estado vazio para qualquer novo gráfico/tabela;
- [ ] manter nomenclatura de métricas coerente com o negócio.
