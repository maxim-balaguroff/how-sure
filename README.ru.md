# how-sure

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24242389.svg)](https://doi.org/10.5281/zenodo.24242389)

[English](README.md) · Русский

Небольшие инструменты и заметки из моей работы геолога-нефтяника. Каждый отвечает на один и тот же вопрос: насколько мы уверены и что сделало бы нас увереннее?

Каждый инструмент умещается в один файл и открывается за несколько секунд. Числа выдуманы или взяты из открытых источников; от заказчиков и работодателей здесь ничего нет. У инструмента, который что-то считает, есть пример с ответом, посчитанным вручную, и встроенные проверки по нему: формулы можно проверить, прежде чем им доверять.

## Инструменты

Инструменты делятся на два семейства. **До того, как потрачены деньги:** что измерять и где, чтобы данные ответили на вопрос, ради которого их покупают (02, магнитная съёмка; 03, мелкое бурение), и сколько может содержать перспективный объект, диапазоном, с данными, которые могли бы изменить решение (04). **После скважины:** что результат говорит о прогнозе (01); он же показывает, насколько широкими должны быть диапазоны в 04.

| | Инструмент | Что делает | Файлы |
|---|---|---|---|
| 01 | [Прогноз против результата](01-prediction-vs-result/README.ru.md) | Разбор после бурения. По каждой цели: прогноз, что вскрыло долото, расхождение, его причина и что меняется в следующей рекомендации. Показывает смещение по группам, как часто держались диапазоны ± с поправкой на случай и попадания по неверной причине. | [Excel](https://github.com/maxim-balaguroff/how-sure/raw/main/01-prediction-vs-result/prediction-vs-result.xlsx) · PDF [RU](01-prediction-vs-result/prediction-vs-result-one-page.ru.pdf) [EN](01-prediction-vs-result/prediction-vs-result-one-page.pdf) |
| 02 | [Проверка магнитной съёмки](02-magnetic-survey-check/README.ru.md) | Что должна разрешить съёмка? Проверяет задуманную магнитную съёмку до того, как её выполнят: для дайки, края силла или штока, поднимется ли тело над шумом, покажутся ли два тела двумя, какой нужен шаг профилей и что меняется между наземной съёмкой, UAV на малой высоте, вертолётом и самолётом. | [Открыть страницу](https://maxim-balaguroff.github.io/how-sure/02-magnetic-survey-check/magnetic-survey-check.html) · [HTML](https://github.com/maxim-balaguroff/how-sure/releases/latest/download/magnetic-survey-check.html) |
| 03 | [Пять скважин: какие пять?](03-shallow-wells-plan/README.ru.md) | Как планировать мелкое стратиграфическое бурение, когда скважин мало: что даёт каждая следующая скважина, почему слабое звено датировка, а не керн, и как первые керны меняют оставшиеся скважины. За ним стоит опубликованная кампания, первая на российском арктическом шельфе: 10 скважин, 300 м керна, 13 стратиграфических подразделений. | [Открыть страницу](https://maxim-balaguroff.github.io/how-sure/03-shallow-wells-plan/shallow-wells-plan.html) · [HTML](https://github.com/maxim-balaguroff/how-sure/releases/latest/download/shallow-wells-plan.html) · PDF [RU](03-shallow-wells-plan/five-wells-one-page.ru.pdf) [EN](03-shallow-wells-plan/five-wells-one-page.pdf) |
| 04 | [Сколько и насколько уверенно?](04-volume-range/README.ru.md) | Геологические ресурсы нефти перспективного объекта как диапазон от P90 до P10: почему нижняя оценка не равна произведению нижних значений, какие параметры дают основной разброс и какие данные могли бы изменить решение. Тот же расчёт есть в таблице Монте-Карло. | [Открыть страницу](https://maxim-balaguroff.github.io/how-sure/04-volume-range/volume-range.html) · [HTML](https://github.com/maxim-balaguroff/how-sure/releases/latest/download/volume-range.html) · [Excel](https://github.com/maxim-balaguroff/how-sure/raw/main/04-volume-range/volume-range.xlsx) · PDF [RU](04-volume-range/volume-range-one-page.ru.pdf) [EN](04-volume-range/volume-range-one-page.pdf) |

[![Лист Summary инструмента 01 на выдуманном примере](01-prediction-vs-result/screenshot-summary.png)](01-prediction-vs-result/README.ru.md)

## Как пользоваться

1. Скачайте файл из папки инструмента или откройте страницу в браузере.
2. Сначала посмотрите проверки. Пока пример на месте, там ALL PASS (инструмент 01, лист Test: ALL 32 PASS; инструмент 02, внизу страницы: ALL 24 PASS; инструмент 03, внизу страницы: ALL 49 PASS; инструмент 04, внизу страницы: ALL 74 PASS, лист Test его таблицы: ALL 38 PASS).
3. Потом внесите свои числа.

Если число выглядит неверным, [откройте issue](https://github.com/maxim-balaguroff/how-sure/issues).

## Лицензия и ссылка

Тексты и шаблоны: [CC BY 4.0](LICENSE). Можно брать и менять, указывая источник.

Как сослаться: Balagurov, M. (2026). *how-sure: small tools and notes from a petroleum geologist's work* (v1.3). Zenodo. [https://doi.org/10.5281/zenodo.24242389](https://doi.org/10.5281/zenodo.24242389). DOI всегда ведёт на последнюю версию; другие форматы даёт кнопка *Cite this repository*.

Сделано с помощью ИИ; геология и проверки мои.

Максим Балагуров · [LinkedIn](https://www.linkedin.com/in/balagurov)
