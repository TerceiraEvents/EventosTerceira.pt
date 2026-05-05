---
layout: default
title: Sugerir um Evento
description: Submete um evento especial para inclusão no calendário dos Eventos da Terceira.
permalink: /pt/suggest/
lang: pt
lang_alt: /suggest/
---

<h2>Sugerir um Evento</h2>

<p class="section-intro">Tens um evento que achas que devia estar aqui? Preenche o formulário abaixo. Vamos rever e adicioná-lo ao site &mdash; normalmente em um ou dois dias.</p>

<form id="suggest-form" class="suggest-form">
  <div class="form-field">
    <label for="name">Nome do Evento <span class="required">*</span></label>
    <input type="text" id="name" name="name" required maxlength="200" placeholder="ex.: Concerto no Teatro Angrense">
  </div>

  <div class="form-field">
    <label for="date">Data <span class="required">*</span></label>
    <input type="date" id="date" name="date" required>
  </div>

  <div class="form-field">
    <label for="time">Hora</label>
    <input type="time" id="time" name="time" placeholder="ex.: 21:30">
    <small>Opcional &mdash; deixa em branco se não souberes</small>
  </div>

  <div class="form-field">
    <label for="venue">Local <span class="required">*</span></label>
    <input type="text" id="venue" name="venue" required maxlength="200" placeholder="ex.: Teatro Angrense">
  </div>

  <div class="form-field">
    <label for="address">Morada</label>
    <input type="text" id="address" name="address" maxlength="300" placeholder="ex.: Rua da Esperança 48-52, Angra do Heroísmo">
  </div>

  <div class="form-field">
    <label for="map_url">Link do Google Maps</label>
    <input type="url" id="map_url" name="map_url" maxlength="500" placeholder="https://maps.app.goo.gl/...">
    <small>Opcional &mdash; cola um link de partilha do Google Maps para marcares a localização exata</small>
  </div>

  <div class="form-field">
    <label for="description">Descrição</label>
    <textarea id="description" name="description" rows="4" maxlength="2000" placeholder="Sobre o que é o evento? Bilheteira, convidados, qualquer coisa que as pessoas devam saber."></textarea>
  </div>

  <div class="form-field">
    <label for="instagram">Link do Instagram</label>
    <input type="url" id="instagram" name="instagram" maxlength="500" placeholder="https://www.instagram.com/p/...">
    <small>Link para uma publicação ou conta de Instagram com mais detalhes do evento</small>
  </div>

  <div class="form-field">
    <label for="image">URL do cartaz / poster</label>
    <input type="url" id="image" name="image" maxlength="500" placeholder="https://...">
    <small>Link para uma imagem do cartaz (por exemplo, do Instagram ou de qualquer URL público). Inclui sempre que possível!</small>
  </div>

  <div class="form-field form-tags">
    <label>Etiquetas</label>
    <small>Escolhe todas as que se aplicam. Ajudam quem visita a filtrar o calendário.</small>
    <div class="tag-chips">
      {% for tag in site.data.event_tags %}
      {%- assign tag_label = tag.label_pt | default: tag.label -%}
      <label class="tag-chip">
        <input type="checkbox" name="tags[]" value="{{ tag.slug }}">
        <span>{{ tag.emoji }} {{ tag_label }}</span>
      </label>
      {% endfor %}
    </div>
  </div>

  <div class="form-field">
    <label for="submitterName">O teu nome</label>
    <input type="text" id="submitterName" name="submitterName" maxlength="100" placeholder="Opcional &mdash; para créditos">
  </div>

  <!-- Honeypot field: hidden from users, bots fill it in -->
  <div style="position:absolute; left:-9999px; opacity:0; pointer-events:none;" aria-hidden="true">
    <label for="website">Website (deixa em branco)</label>
    <input type="text" id="website" name="website" tabindex="-1" autocomplete="off">
  </div>

  <button type="submit" id="submit-btn" class="form-submit">Enviar Evento</button>

  <div id="form-message" class="form-message" style="display:none;"></div>
</form>

<div class="venue-card" style="margin-top:2rem;">
  <div class="venue-regulars">
    <p><strong>Outras formas de sugerir eventos:</strong></p>
    <ul>
      <li>Abre a app móvel <strong>Eventos da Terceira</strong> e toca em "Sugerir Evento"</li>
      <li>Submete um pull request no <a href="https://github.com/TerceiraEvents/EventosTerceira.pt">GitHub</a> se és da área técnica</li>
      <li>Manda DM a <a href="https://www.instagram.com/chrisrackauckas/">@chrisrackauckas</a> no Instagram</li>
    </ul>
  </div>
</div>

<style>
.suggest-form {
  max-width: 640px;
  margin: 1.5rem 0 2rem;
}
.form-field {
  margin-bottom: 1.25rem;
}
.form-field label {
  display: block;
  font-weight: 600;
  color: var(--primary, #2d5016);
  margin-bottom: 0.4rem;
  font-size: 0.95rem;
}
.form-field .required {
  color: #c0392b;
}
.form-field input,
.form-field textarea {
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: 1px solid #d8d4c4;
  border-radius: 6px;
  font-family: inherit;
  font-size: 1rem;
  background: #fff;
  box-sizing: border-box;
  color: #2c2c2c;
}
.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: var(--primary, #2d5016);
  box-shadow: 0 0 0 3px rgba(45, 80, 22, 0.1);
}
.form-field textarea {
  resize: vertical;
  min-height: 90px;
}
.form-field.form-tags > label {
  margin-bottom: 0.25rem;
}
.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.6rem;
}
.tag-chip {
  display: inline-block;
  cursor: pointer;
}
.tag-chip input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
  width: 0;
  height: 0;
}
.tag-chip span {
  display: inline-block;
  padding: 0.45rem 0.85rem;
  background: #fff;
  border: 1px solid #d8d4c4;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #555;
  transition: all 0.15s;
  user-select: none;
}
.tag-chip:hover span {
  border-color: var(--primary, #2d5016);
  background: #f6f5ef;
}
.tag-chip input:checked + span {
  background: var(--primary, #2d5016);
  border-color: var(--primary, #2d5016);
  color: #fff;
}
.tag-chip input:focus-visible + span {
  box-shadow: 0 0 0 3px rgba(45, 80, 22, 0.25);
}
.form-field small {
  display: block;
  margin-top: 0.3rem;
  color: #777;
  font-size: 0.85rem;
}
.form-submit {
  background: var(--primary, #2d5016);
  color: #fff;
  border: none;
  padding: 0.85rem 1.75rem;
  border-radius: 6px;
  font-family: inherit;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}
.form-submit:hover:not(:disabled) {
  background: #1a3009;
}
.form-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.form-message {
  margin-top: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 6px;
  font-size: 0.95rem;
}
.form-message.success {
  background: #e8f5e0;
  border-left: 3px solid var(--primary, #2d5016);
  color: #1a3009;
}
.form-message.error {
  background: #fbeaea;
  border-left: 3px solid #c0392b;
  color: #8a1e1e;
}
</style>

<script>
(function() {
  var SUBMIT_URL = 'https://event-submit-worker.terceriaevents.workers.dev/submit-event';
  var form = document.getElementById('suggest-form');
  var btn = document.getElementById('submit-btn');
  var msgBox = document.getElementById('form-message');

  function showMessage(text, type) {
    msgBox.textContent = text;
    msgBox.className = 'form-message ' + type;
    msgBox.style.display = 'block';
  }

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    msgBox.style.display = 'none';

    var data = {};
    var tagList = [];
    new FormData(form).forEach(function(value, key) {
      if (key === 'tags[]') {
        var slug = String(value).trim();
        if (slug) tagList.push(slug);
        return;
      }
      var trimmed = String(value).trim();
      if (trimmed) data[key] = trimmed;
    });
    if (tagList.length) data.tags = tagList;

    // Honeypot check — silently pretend success to not tip off bots
    if (data.website) {
      showMessage('Obrigado! O teu evento foi submetido para revisão.', 'success');
      form.reset();
      return;
    }

    // Client-side required-field check
    if (!data.name || !data.date || !data.venue) {
      showMessage('Preenche por favor o nome do evento, a data e o local.', 'error');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'A enviar...';

    try {
      var response = await fetch(SUBMIT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      var result = await response.json().catch(function() { return {}; });

      if (response.ok && result.success) {
        showMessage('Obrigado! O teu evento foi submetido para revisão.', 'success');
        form.reset();
      } else {
        var errMsg = result.error || 'Algo correu mal. Tenta novamente mais tarde.';
        showMessage(errMsg, 'error');
      }
    } catch (err) {
      showMessage('Erro de rede. Verifica a tua ligação e tenta novamente.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Enviar Evento';
    }
  });
})();
</script>
