#!/bin/bash

# Удалите старые сборки
rm -rf dist/ build/ *.egg-info/

# Функция для автоматического поднятия версии
increment_version() {
    local version=$1
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    local patch=$(echo $version | cut -d. -f3)

    patch=$((patch + 1))
    echo "$major.$minor.$patch"
}

# Получаем текущую версию из setup.py
CURRENT_VERSION=$(grep "version=" setup.py | sed -E "s/.*version=\"([0-9]+\.[0-9]+\.[0-9]+)\".*/\1/")
echo "Текущая версия: $CURRENT_VERSION"

# Поднимаем версию
NEW_VERSION=$(increment_version $CURRENT_VERSION)
echo "Новая версия: $NEW_VERSION"

# Обновляем версию в setup.py
sed -i.bak -E "s/version=\"[0-9]+\.[0-9]+\.[0-9]+\"/version=\"$NEW_VERSION\"/" setup.py
rm -f setup.py.bak

# Обновляем версию в pyproject.toml
sed -i.bak -E "s/version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$NEW_VERSION\"/" pyproject.toml
rm -f pyproject.toml.bak

echo "Версия обновлена с $CURRENT_VERSION на $NEW_VERSION"

# Соберите заново
. venv/bin/activate
pip install -r requirements.txt
python3 -m build

# Проверьте
twine check dist/*

# Проверяем наличие токена
if [ -z "$PYPI_TOKEN" ]; then
    echo "Ошибка: Переменная окружения PYPI_TOKEN не установлена"
    echo "Установите токен: export PYPI_TOKEN=your-token-here"
    exit 1
fi

# Публикуйте с использованием токена
twine upload dist/* -u __token__ -p $PYPI_TOKEN

echo "Публикация завершена успешно!"