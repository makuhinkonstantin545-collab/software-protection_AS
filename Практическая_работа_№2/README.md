# Практическое занятие № 2. Развёртывание GitLab и GitLab Runner на виртуальной машине

**Студент:** Макухин Константин Геннадьевич, группа 25_КМ_ИБ2
**Дисциплина:** Защита ПО

## 1. Цель работы

Освоить установку и первичную настройку собственного экземпляра GitLab и GitLab Runner на виртуальной машине, выполнить первый push в созданный репозиторий, настроить CI/CD-пайплайн и проверить его выполнение Runner'ом.

## 2. Окружение

| Компонент | Значение |
|---|---|
| Хост | Windows 11 Pro, WSL2 (Ubuntu) |
| Виртуализация | Oracle VirtualBox, сетевой мост (Bridged) |
| ВМ | Ubuntu Server 24.04.5 LTS, 8 ГБ RAM, 4 vCPU, диск 40 ГБ (динамический) |
| IP ВМ | 172.20.10.14 |
| GitLab | GitLab CE 19.5.1 (пакет из репозитория packages.gitlab.com) |
| GitLab Runner | 19.5.2, executor `docker`, образ `alpine:latest`, тег `linux` |
| Docker | docker.io (нужен executor `docker` на самой ВМ) |

## 3. Ход работы

### Этап 1. Подготовка и подключение к ВМ

Ubuntu Server установлена в VirtualBox с OpenSSH. Проверены сеть и подключение по SSH с Windows.

Команды на ВМ:

```bash
ip -br a
ping -c 4 8.8.8.8
ssh pepe@172.20.10.14
```

Результат: ВМ получила адрес 172.20.10.14, интернет доступен, подключение по SSH работает.

![SSH-сессия на ВМ](screenshots/01-ssh-vm.png)

![Адрес ВМ и проверка сети](screenshots/02-vm-ping-ip.png)

### Этап 2. Установка GitLab CE

Обновление системы и зависимости:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl openssh-server ca-certificates tzdata perl
sudo apt install -y postfix          # Internet Site
curl https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | sudo bash
sudo EXTERNAL_URL="http://172.20.10.14" apt install -y gitlab-ce
```

![Распаковка GitLab](screenshots/03-gitlab-install-progress.png)

Проверка служб:

```bash
sudo gitlab-ctl status
```

Все службы (puma, nginx, gitaly, postgresql, redis, sidekiq и др.) в статусе `run`.

### Этап 3. Пароль root и вход

Временный пароль находится в `/etc/gitlab/initial_root_password` (удаляется через 24 часа). Вход выполнен под root, при первом входе пароль сменён.

![Первый вход в GitLab](screenshots/04-gitlab-first-login.png)

### Этап 4. Проект и Runner

**4.1. Проект.** Создан проект `test-project` (Private). Репозиторий пустой, GitLab выдаёт инструкцию с командами Git.

![Проект создан](screenshots/05-project-created.png)

**4.2. Runner.** В настройках проекта создан Runner с тегом `linux`. На ВМ выполнены установка и регистрация:

```bash
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
sudo apt install -y gitlab-runner docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker gitlab-runner
sudo gitlab-runner register --url http://172.20.10.14 --executor docker --docker-image alpine:latest --description my-runner --tag-list linux
sudo gitlab-runner status
```

Проверка: `gitlab-runner verify` вернул `is valid`, служба `active (running)`, Runner в GitLab в статусе **Online**.

![Runner online](screenshots/06-runner-online.png)

### Этап 5. Первый push

На рабочей машине (WSL) создан тестовый проект, сгенерирован ключ `ed25519`, публичная часть добавлена в профиль GitLab (Edit profile → SSH Keys). Проверка доступа: `ssh -T git@172.20.10.14` вернул `Welcome to GitLab, @root!`.

```bash
mkdir ~/test-project && cd ~/test-project
echo "# Test Project" > README.md
git init -b main
git add README.md && git commit -m "Initial commit"
git remote add origin git@172.20.10.14:root/test-project.git
git push -u origin main
```

Результат: `[new branch] main -> main`, файл `README.md` виден в GitLab.

### Задание 1. Файл и коммит

```bash
echo "Hello from GitLab!" > hello.txt
git add hello.txt && git commit -m "feat: add hello.txt"
git push
```

Коммит `a562039`, push `3b25dd7..a562039 main -> main`.

### Задание 2. CI/CD

Создан файл `.gitlab-ci.yml`:

```yaml
stages:
  - test

job1:
  stage: test
  tags:
    - linux
  script:
    - echo "CI/CD is working!"
```

**Проблема и её решение.** Первый pipeline (коммит `f32fc2f`) завис в статусе **Pending** с пометкой «The project doesn't have any runners online assigned to it». Причина: Runner зарегистрирован с тегом `linux`, а задание без тега, и Runner его не берёт. Добавлена строка `tags: [linux]` — после этого задание выполнилось.

![Задание в Pending без тега](screenshots/08-job-stuck-no-tag.png)

![Pipeline в Pending](screenshots/07-pipeline-pending.png)

Успешный запуск (коммит `ae6d6493`):

![Список заданий](screenshots/09-jobs-list.png)

![Журнал задания: Passed](screenshots/10-job-log-passed.png)

В журнале видно: Runner `#1` (bgJe0mz9) клонирует репозиторий, выполняет `echo`, выводит `CI/CD is working!` и завершает задание с `Job succeeded`.

### Задание 3. Ветвление и Merge Request

```bash
git checkout -b feature/update-readme
echo "Раздел About this project" >> README.md
git add README.md && git commit -m "docs: add About section to README"
git push origin feature/update-readme
```

Создан Merge Request !1 (`feature/update-readme` → `main`). Первая проверка блокировала слияние «1 check failed», пока pipeline не завершился. После успешной проверки (pipeline #3 passed) слияние выполнено, ветка удалена, коммит слияния `70288eb2` в `main`.

![Merge request создан](screenshots/11-mr-created.png)

![Merge request слит](screenshots/12-mr-merged.png)

## 4. Ответы на контрольные вопросы

**1. Минимальные требования к ВМ и почему они важны?**
GitLab CE требует минимум 4 ГБ RAM (рекомендуется 8 ГБ и больше) и около 10 ГБ свободного места на диске под пакет и данные. GitLab запускает множество служб одновременно: puma, sidekiq, gitaly, postgresql, redis, nginx и мониторинг. При нехватке памяти службы падают или работают очень медленно, а установка может не завершиться. В работе использовано 8 ГБ RAM и 4 vCPU.

**2. Для чего используется Postfix?**
Postfix — почтовый агент (MTA), через который GitLab отправляет письма: подтверждение регистрации, сброс пароля, уведомления о событиях. При установке выбран тип «Internet Site». Для практики почта не обязательна, но без Postfix GitLab выдаёт предупреждения в процессе настройки.

**3. Какой файл содержит временный пароль root и что с ним происходит через 24 часа?**
Файл `/etc/gitlab/initial_root_password`. GitLab создаёт его при первом запуске и автоматически удаляет через 24 часа. Поэтому пароль нужно скопировать и сменить сразу после первого входа.

**4. Что такое GitLab Runner и его основные функции?**
Runner — отдельная программа-исполнитель. GitLab только хранит и распределяет задания из `.gitlab-ci.yml`, а Runner: опрашивает GitLab на наличие заданий, берёт подходящее по тегам, запускает их в выбранном исполнителе (executor), передаёт журнал и итоговый статус обратно в GitLab.

**5. В чём разница между executor docker и shell?**
- **shell** выполняет команды прямо на хосте от имени пользователя `gitlab-runner`. Окружение общее, результаты предыдущих заданий влияют на следующие, а ошибка в скрипте может повлиять на саму ВМ.
- **docker** запускает каждое задание в отдельном контейнере из указанного образа (здесь `alpine:latest`). Окружение чистое и воспроизводимое, задания изолированы друг от друга и от хоста. Требует установленного Docker и прав у пользователя Runner.

**6. Последовательность действий при добавлении SSH-ключа в GitLab.**
1. На клиенте генерируется пара ключей: `ssh-keygen -t ed25519 -C "email"`. Приватный ключ (`id_ed25519`) остаётся на клиенте.
2. Публичная часть (`id_ed25519.pub`) копируется: `cat ~/.ssh/id_ed25519.pub`.
3. В GitLab: Edit profile → SSH Keys → вставка ключа в поле Key → Add key.
4. Проверка: `ssh -T git@<адрес_GitLab>` должен вернуть приветствие с именем пользователя.
Благодаря этому `git push` по SSH проходит без пароля, а приватный ключ никуда не передаётся.

**7. Как проверить, что GitLab Runner зарегистрирован и активен?**
- на ВМ: `sudo gitlab-runner verify` (вывод `is valid`) и `sudo gitlab-runner status` (`Service is running`);
- в GitLab: Settings → CI/CD → Runners, Runner со статусом **Online** и своим тегом.
- Дополнительный признак: задание получает статус Passed, а в журнале указан Runner по имени.

**8. Где в веб-интерфейсе GitLab просмотреть историю выполнения пайплайнов?**
В проекте: **Build → Pipelines** (список всех запусков, статусы и коммиты). Открыв конкретный pipeline, видно его задания, а по ссылке на задание — полный журнал выполнения. Список всех заданий отдельно доступен в **Build → Jobs**.

## 5. Выводы

Установлен GitLab CE и GitLab Runner на виртуальной машине Ubuntu, создан проект, настроен доступ по SSH-ключу, выполнены push и три задания. Pipeline выполнен Runner'ом с тегом `linux`, Merge Request проведён через проверку CI. Главная трудность — задание без тега не бралось Runner'ом; это наглядно показало, как метки связывают задания и исполнители.
