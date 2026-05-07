# Storymaker

Painel interno em Django para gerar campanhas visuais de informática com dois modos de marca:
- `Blast`
- `Beta`

O sistema foi estruturado para:
- criar projetos individuais
- criar projetos em massa a partir de promoções coladas em texto
- gerar conceito de campanha
- gerar `2` imagens por padrão para cada projeto
- salvar os prompts reais enviados
- rodar tudo de forma assíncrona com `Celery + Redis`

## Estado atual
- Home operacional fora do admin em `/`
- Login aproveita o usuário do Django admin
- Projetos com modo visual `Blast/Beta`
- Cada geração cria `2` variantes de imagem por padrão
- Fluxo assíncrono com status na tela
- Criação em massa promocional com recorte automático de promoções
- Fontes RSS iniciais semeadas automaticamente no deploy

## Stack
- Python `3.12`
- Django `5.2`
- Postgres via `DATABASE_URL`
- Celery + Redis para filas
- OpenAI para texto/imagem quando houver chave
- Fallback local com placeholder SVG quando não houver geração real de imagem

## URLs principais
- `/` painel principal
- `/projects/new/` novo projeto
- `/projects/<slug>/` detalhe do projeto
- `/admin/` backoffice técnico

## Conceitos principais

### 1. Projeto
Cada projeto tem:
- tipo: `news`, `generic`, `promotional`
- modo visual: `Blast` ou `Beta`
- brief / tema / preço
- um único campo de ajuste: `adjustment request`

### 2. Conceito
O conceito é o texto e a direção visual da campanha:
- headline
- subheadline
- body
- preço
- CTA
- direção visual
- prompt real enviado para gerar esse conceito

### 3. Variantes
Cada conceito gera `2` variantes de imagem por padrão.

Cada variante salva:
- prompt real enviado para imagem
- arquivo gerado
- status
- resposta do provider

### 4. Lote em massa
O lote em massa sempre cria projetos `promotional`.

Você cola texto com promoções e o sistema:
1. recorta as promoções
2. cria um projeto por promoção
3. gera conceito automaticamente
4. gera 2 imagens por projeto

## Fluxo do usuário

### Projeto individual
1. Acesse `/projects/new/`
2. Escolha `Blast` ou `Beta`
3. Escolha o tipo de projeto
4. Preencha o tema, brief e preço se necessário
5. Salve
6. Entre no projeto
7. Clique em `Gerar ou regerar conceito + 2 imagens`
8. Aguarde a tela atualizar sozinha
9. Compare as 2 variantes
10. Marque a melhor como selecionada

### Criação em massa
1. Acesse `/`
2. Vá em `Criação em massa`
3. Escolha `Blast` ou `Beta`
4. Cole as promoções
5. Clique em `Gerar lote assíncrono`
6. O lote vai aparecer com status
7. Os projetos criados também aparecerão na galeria principal

## Formato esperado para promoções em massa
Pode ser irregular. O parser tenta separar blocos por linhas em branco ou por linhas com preço.

Exemplo:

```text
NOTEBOOK LENOVO IDEAPAD
Ryzen 7 16GB SSD 512GB Tela Full HD
R$ 3.999

PC GAMER RTX 4060
Ryzen 5 5600 16GB SSD 1TB
R$ 5.499
```

## Modo visual

### Blast
- roxo dominante
- estética premium de tecnologia
- layout clean com produto hero e conversão forte

### Beta
- azul corporativo dominante
- varejo promocional direto
- preço extremamente dominante
- fundo clean desfocado

## Importante sobre o processamento assíncrono
As requisições não geram conceito e imagem dentro da request HTTP.

Elas apenas entram na fila.

Para isso funcionar, o `worker` precisa estar rodando.

Se o projeto ficar parado em:
- `Queued`
- `Generating concept`
- `Generating images`

verifique se o serviço `worker` está ativo.

## Local setup
1. Criar venv:

```bash
python3 -m venv .venv
```

2. Instalar dependências:

```bash
./.venv/bin/pip install -r requirements.txt
```

3. Criar `.env`:

```bash
cp .env.example .env
```

4. Migrar banco:

```bash
./.venv/bin/python manage.py migrate
```

5. Semear fontes RSS:

```bash
./.venv/bin/python manage.py seed_initial_data
```

6. Criar admin:

```bash
./.venv/bin/python manage.py createsuperuser
```

7. Em desenvolvimento, se quiser rodar tudo localmente sem worker separado, você pode usar:

```env
CELERY_TASK_ALWAYS_EAGER=True
```

8. Rodar servidor:

```bash
./.venv/bin/python manage.py runserver 0.0.0.0:8015
```

9. Rodar worker em outro terminal quando estiver testando async real:

```bash
./.venv/bin/celery -A config worker --loglevel=info
```

## Easypanel com um único app

Se voce esta rodando apenas **um app** no Easypanel, sem `docker compose`, este projeto agora suporta esse modo diretamente.

O `CMD` padrao do container sobe junto:
- `redis-server` local quando `REDIS_URL` estiver apontando para `127.0.0.1` ou `localhost`
- `gunicorn`
- `celery worker`

Isso permite que a fila funcione mesmo com um unico app.

### O que fazer agora no seu caso
1. Faça redeploy do app no Easypanel com o código mais novo.
2. O container vai rodar `migrate` automaticamente no startup.
3. As novas migrations de reconciliação vão corrigir o schema legado do banco.
4. O container também vai subir o worker no mesmo app.
5. Abra `/` e teste um projeto novo.

### Se ainda der erro de schema
Entre no console do app e rode:

```bash
python manage.py migrate
python manage.py seed_initial_data
```

## VPS / Docker Compose

### 1. Subir o stack
```bash
docker compose up -d --build
```

O compose sobe:
- `web`
- `worker`
- `redis`

### 2. Criar o superusuário

Se estiver no host da VPS:

```bash
docker compose exec web python manage.py createsuperuser
```

Se estiver no console do container no Easypanel:

```bash
python manage.py createsuperuser
```

### 3. Abrir o painel
- `/` para o painel principal
- `/admin/` para o admin técnico

## Easypanel

### Configuração mínima do `.env`
```env
DEBUG=False
ALLOWED_HOSTS=blast-storymaker.0ksds9.easypanel.host
CSRF_TRUSTED_ORIGINS=https://blast-storymaker.0ksds9.easypanel.host
APP_PORT=8015
USE_X_FORWARDED_HOST=True
USE_X_FORWARDED_PORT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=False
OPENAI_API_KEY=your-openai-key
```

### Atenção
- Em app único no Easypanel, o `worker` agora sobe dentro do mesmo container por padrão.
- Se os projetos continuarem em `Queued`, faça um redeploy para garantir que a imagem nova foi aplicada.
- Se o startup quebrar por schema legado, rode `python manage.py migrate` manualmente no console do app.

## Portas bloqueadas na VPS
Não usar:
- `80`
- `8000`
- `8011`
- `8085`
- `8086`
- `8091`
- `8501`

Porta segura atual:
- `8015`

## Comandos úteis
```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py seed_initial_data
./.venv/bin/python manage.py createsuperuser
./.venv/bin/celery -A config worker --loglevel=info
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

## Observações
- O admin continua existindo como backoffice, mas o fluxo principal agora fica na home `/`.
- O único campo de ajuste do projeto é `adjustment request`.
- O conceito e cada variante mostram o prompt real salvo.
- Sem `OPENAI_API_KEY`, o sistema continua funcional usando conceitos fallback + SVG placeholder.
