# Удалите старые сборки
rm -rf dist/ build/ *.egg-info/

# Соберите заново
python -m build

# Проверьте
twine check dist/*

# Публикуйте
twine upload dist/*