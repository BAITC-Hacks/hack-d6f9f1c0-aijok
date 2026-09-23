const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('.main-nav');
if (menuButton && navigation) {
  menuButton.addEventListener('click', () => {
    const open = navigation.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(open));
  });
  navigation.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => navigation.classList.remove('open')));
}

const form = document.querySelector('#match-form');
const dateInput = document.querySelector('.date-input');
function parseDisplayDate(value) {
  const match = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(value);
  if (!match) return null;
  const [, day, month, year] = match;
  const candidate = new Date(`${year}-${month}-${day}T00:00:00Z`);
  return candidate.getUTCFullYear() === Number(year) && candidate.getUTCMonth() + 1 === Number(month) && candidate.getUTCDate() === Number(day)
    ? `${year}-${month}-${day}` : null;
}
if (dateInput) {
  dateInput.addEventListener('input', () => {
    const digits = dateInput.value.replace(/\D/g, '').slice(0, 8);
    dateInput.value = [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 8)].filter(Boolean).join('.');
    dateInput.setCustomValidity('');
  });
}
if (form) {
  form.addEventListener('submit', (event) => {
    const isoDate = parseDisplayDate(dateInput.value);
    const min = '2026-09-23';
    const max = '2026-12-31';
    if (!isoDate || isoDate < min || isoDate > max) {
      event.preventDefault();
      dateInput.setCustomValidity('Введите дату от 23.09.2026 до 31.12.2026 в формате ДД.ММ.ГГГГ.');
      dateInput.reportValidity();
      return;
    }
    const button = form.querySelector('.submit');
    button.querySelector('span').textContent = 'Подбираем…';
    button.disabled = true;
  });
}

const modal = document.querySelector('#demo-modal');
document.querySelectorAll('[data-modal-message]').forEach((button) => button.addEventListener('click', () => {
  modal.querySelector('p').textContent = button.dataset.modalMessage;
  modal.showModal();
}));
if (modal) {
  modal.querySelectorAll('.modal-close, .modal-confirm').forEach((button) => button.addEventListener('click', () => modal.close()));
  modal.addEventListener('click', (event) => { if (event.target === modal) modal.close(); });
}

const assistantAnswers = {
  'как выбрать подрядчика?': 'Укажите город, дату, формат мероприятия, нужную категорию и бюджет. При желании добавьте длительность и язык — система учтёт их при подборе.',
  'почему мне показали только двух?': 'После обязательной проверки осталось только два профиля. Остальные могли быть заняты в эту дату, превышать бюджет, не поддерживать формат или запрошенную длительность.',
  'что означает совпадение?': 'Это прозрачная оценка соответствия: она учитывает язык, запас бюджета, длительность и полноту параметров профиля. Случайные числа не используются.',
  'почему изменилась выдача после смены даты?': 'У каждого подрядчика есть календарь busy_dates. При смене даты занятые профили исключаются, поэтому состав и порядок доступных кандидатов может измениться.',
  'что такое синтетический профиль?': 'Это профиль, добавленный в датасет для демонстрации сценариев. На карточке он всегда отмечен меткой «Синтетический профиль».'
};
const fallbackAnswer = 'Я пока работаю в демонстрационном режиме. Попробуйте один из предложенных вопросов.';
const chatLog = document.querySelector('#chat-log');
const assistantForm = document.querySelector('#assistant-form');
function askAssistant(question) {
  if (!chatLog || !question.trim()) return;
  const normalized = question.trim().toLocaleLowerCase('ru-RU');
  const userBubble = document.createElement('div'); userBubble.className = 'bubble user'; userBubble.textContent = question.trim();
  const assistantBubble = document.createElement('div'); assistantBubble.className = 'bubble assistant'; assistantBubble.textContent = assistantAnswers[normalized] || fallbackAnswer;
  chatLog.append(userBubble, assistantBubble); chatLog.scrollTop = chatLog.scrollHeight;
}
document.querySelectorAll('.quick-questions button').forEach((button) => button.addEventListener('click', () => askAssistant(button.textContent)));
if (assistantForm) assistantForm.addEventListener('submit', (event) => { event.preventDefault(); const input = assistantForm.querySelector('input'); askAssistant(input.value); input.value = ''; });
