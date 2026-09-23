const form = document.querySelector('#match-form');

if (form) {
  form.addEventListener('submit', () => {
    const button = form.querySelector('.submit');
    button.querySelector('span').textContent = 'Подбираем…';
    button.disabled = true;
  });
}
