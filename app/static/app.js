// Основные сценарии работают без JavaScript; даты дополняются местным временем.
for (const element of document.querySelectorAll('time[datetime]')) {
  const date = new Date(element.dateTime);
  if (!Number.isNaN(date.getTime())) {
    element.textContent = new Intl.DateTimeFormat('ru-RU', {
      dateStyle: 'medium', timeStyle: 'short',
    }).format(date);
    element.title = `Часовой пояс: ${Intl.DateTimeFormat().resolvedOptions().timeZone}`;
  }
}
