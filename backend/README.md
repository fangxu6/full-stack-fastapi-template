# FastAPI Project - Backend

## Requirements

* [Docker](https://www.docker.com/).
* [uv](https://docs.astral.sh/uv/) for Python package and environment management.

## Docker Compose

Start the local development environment with Docker Compose following the guide in [../development.md](../development.md).

## General Workflow

By default, the dependencies are managed with [uv](https://docs.astral.sh/uv/), go there and install it.

From `./backend/` you can install all the dependencies with:

```console

$ uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

Then you can activate the virtual environment with:

```console
$ source .venv/bin/activate
```

### windows环境
```
# 1. 确保Python已安装并添加到环境变量
python --version  # 或 py --version（Windows多版本Python）

# 2. 重新创建虚拟环境
python -m venv .venv

# 3. 再次执行激活脚本
& .\.venv\Scripts\Activate.ps1
```

Make sure your editor is using the correct Python virtual environment, with the interpreter at `backend/.venv/bin/python`.

Backend code follows the layered structure:

- Models (database tables): `./backend/app/models/`
- Schemas (request/response DTOs): `./backend/app/schemas/`
- CRUD (atomic DB operations): `./backend/app/crud/`
- Services (business logic): `./backend/app/services/`
- API routes: `./backend/app/api/routes/`

## VS Code

There are already configurations in place to run the backend through the VS Code debugger, so that you can use breakpoints, pause and explore variables, etc.

The setup is also already configured so you can run the tests through the VS Code Python tests tab.

## PyCharm

If you run backend in PyCharm, use **Module mode** (not Script mode) to start `uvicorn`.

Recommended Run/Debug configuration:

- **Run kind**: `Module name`
- **Module name**: `uvicorn`
- **Parameters**: `app.main:app --reload`
- **Working directory**: `backend/`
- **Python interpreter**: `backend/.venv/Scripts/python.exe` (Windows) or `backend/.venv/bin/python` (macOS/Linux)

Why this matters:

- `uvicorn` is a third-party Python package (ASGI server), installed into your virtual environment.
- It is imported as a Python module, not a file under `backend/app/`.
- So `backend/app/` not containing `uvicorn` is expected.
- If Script mode is used with `uvicorn` as file path, PyCharm tries to open a local file named `uvicorn` and raises `FileNotFoundError`.

Quick terminal check from `backend/`:

```console
$ uv run uvicorn app.main:app --reload
```

## Docker Compose Override

During development, you can change Docker Compose settings that will only affect the local development environment in the file `compose.override.yml`.

The changes to that file only affect the local development environment, not the production environment. So, you can add "temporary" changes that help the development workflow.

For example, the directory with the backend code is synchronized in the Docker container, copying the code you change live to the directory inside the container. That allows you to test your changes right away, without having to build the Docker image again. It should only be done during development, for production, you should build the Docker image with a recent version of the backend code. But during development, it allows you to iterate very fast.

There is also a command override that runs `uvicorn app.main:app --reload` instead of the default production command. It starts a single server process (instead of multiple, as would be for production) and reloads the process whenever the code changes. Have in mind that if you have a syntax error and save the Python file, it will break and exit, and the container will stop. After that, you can restart the container by fixing the error and running again:

```console
$ docker compose watch
```

There is also a commented out `command` override, you can uncomment it and comment the default one. It makes the backend container run a process that does "nothing", but keeps the container alive. That allows you to get inside your running container and execute commands inside, for example a Python interpreter to test installed dependencies, or start the development server that reloads when it detects changes.

To get inside the container with a `bash` session you can start the stack with:

```console
$ docker compose watch
```

and then in another terminal, `exec` inside the running container:

```console
$ docker compose exec backend bash
```

You should see an output like:

```console
root@7f2607af31c3:/app#
```

that means that you are in a `bash` session inside your container, as a `root` user, under the `/app` directory, this directory has another directory called "app" inside, that's where your code lives inside the container: `/app/app`.

There you can use the `uvicorn app.main:app --reload` command to run the debug live reloading server.

```console
$ uvicorn app.main:app --reload
```

...it will look like:

```console
root@7f2607af31c3:/app# uvicorn app.main:app --reload
```

and then hit enter. That runs the live reloading server that auto reloads when it detects code changes.

Nevertheless, if it doesn't detect a change but a syntax error, it will just stop with an error. But as the container is still alive and you are in a Bash session, you can quickly restart it after fixing the error, running the same command ("up arrow" and "Enter").

...this previous detail is what makes it useful to have the container alive doing nothing and then, in a Bash session, make it run the live reload server.

## Backend tests

To test the backend run:

```console
$ POSTGRES_DB=aiadmin_test bash ./scripts/test.sh
```

Backend tests are destructive and refuse to run unless `POSTGRES_DB` points to
an isolated database whose name ends with `_test` or `_pytest`. Do not run them
against the daily development database.

For a local PostgreSQL setup:

```powershell
createdb -U postgres aiadmin_test
cd backend
$env:POSTGRES_DB = "aiadmin_test"
uv run alembic upgrade head
uv run python app/initial_data.py
uv run pytest tests/
```

The tests run with Pytest, modify and add tests to `./backend/tests/`.

## Scheduled tasks

After upgrading migrations, initialize the built-in scheduled tasks before
starting the API, Celery Worker, and Celery Beat processes:

```powershell
uv run alembic upgrade head
uv run python app/initial_data.py
```

Set `SCHEDULED_TASK_ALERT_RECIPIENTS` to a comma-separated operations mailing
list outside local development. Worker and Beat refuse to start in staging and
production when SMTP or this recipient list is missing.

If you use GitHub Actions the tests will run automatically.

### Test running stack

If your stack is already up and you just want to run the tests, you can use:

```bash
docker compose exec backend bash scripts/tests-start.sh
```

That `/app/scripts/tests-start.sh` script just calls `pytest` after making sure that the rest of the stack is running. If you need to pass extra arguments to `pytest`, you can pass them to that command and they will be forwarded.

For example, to stop on first error:

```bash
docker compose exec backend bash scripts/tests-start.sh -x
```

### Test Coverage

When the tests are run, a file `htmlcov/index.html` is generated, you can open it in your browser to see the coverage of the tests.

## Migrations

As during local development your app directory is mounted as a volume inside the container, you can also run the migrations with `alembic` commands inside the container and the migration code will be in your app directory (instead of being only inside the container). So you can add it to your git repository.

Make sure you create a "revision" of your models and that you "upgrade" your database with that revision every time you change them. As this is what will update the tables in your database. Otherwise, your application will have errors.

* Start an interactive session in the backend container:

```console
$ docker compose exec backend bash
```

* Alembic is already configured to import your SQLModel models from `./backend/app/models.py`.

* After changing a model (for example, adding a column), inside the container, create a revision, e.g.:

```console
$ alembic revision --autogenerate -m "Add column last_name to User model"
```

* Commit to the git repository the files generated in the alembic directory.

* After creating the revision, run the migration in the database (this is what will actually change the database):

```console
$ alembic upgrade head
```

If you don't want to use migrations at all, uncomment the lines in the file at `./backend/app/core/db.py` that end in:

```python
SQLModel.metadata.create_all(engine)
```

and comment the line in the file `scripts/prestart.sh` that contains:

```console
$ alembic upgrade head
```

If you don't want to start with the default models and want to remove them / modify them, from the beginning, without having any previous revision, you can remove the revision files (`.py` Python files) under `./backend/app/alembic/versions/`. And then create a first migration as described above.

## Email Templates

The email templates are in `./backend/app/email-templates/`. Here, there are two directories: `build` and `src`. The `src` directory contains the source files that are used to build the final email templates. The `build` directory contains the final email templates that are used by the application.

Before continuing, ensure you have the [MJML extension](https://github.com/mjmlio/vscode-mjml) installed in your VS Code.

Once you have the MJML extension installed, you can create a new email template in the `src` directory. After creating the new email template and with the `.mjml` file open in your editor, open the command palette with `Ctrl+Shift+P` and search for `MJML: Export to HTML`. This will convert the `.mjml` file to a `.html` file and now you can save it in the build directory.
