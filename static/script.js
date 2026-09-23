const form = document.querySelector('#match-form');
if (form) form.addEventListener('submit', () => { const button = form.querySelector('.submit'); button.querySelector('span').textContent = 'Подбираем…'; button.disabled = true; });

document.querySelectorAll('[data-demo-contact]').forEach((button) => button.addEventListener('click', () => {
  const note = button.closest('.card').querySelector('.contact-note');
  note.textContent = 'Контакт скрыт в демо';
}));

const answers = {
  'как выбрать подрядчика?': 'Сравните объяснение, бюджетный запас, формат, языки и допустимую длительность. Итоговое решение остаётся за вами.',
  'почему показали меньше трёх?': 'TOP-3 — это максимум. Если обязательным условиям соответствуют один или два профиля, сервис честно показывает только их.',
  'что означает совпадение?': 'Это детерминированная оценка по языку, запасу бюджета, длительности и наполненности профиля, а не вероятность и не гарантия качества.',
  'почему выдача изменилась после смены даты?': 'Календарь busy_dates исключает занятых в конкретный день подрядчиков, поэтому другая дата может изменить состав и порядок выдачи.',
  'что такое синтетический профиль?': 'Это искусственно созданный демонстрационный профиль, а не реальный подрядчик.'
};
const response = document.querySelector('#assistant-response');
function answer(question) { if (response) response.textContent = answers[question.trim().toLowerCase()] || 'Я пока работаю в демонстрационном режиме. Попробуйте один из предложенных вопросов.'; }
document.querySelectorAll('[data-question]').forEach((button) => button.addEventListener('click', () => answer(button.dataset.question)));
const send = document.querySelector('#assistant-send');
if (send) send.addEventListener('click', () => answer(document.querySelector('#assistant-input').value));
