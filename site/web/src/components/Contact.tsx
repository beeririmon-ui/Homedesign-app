/**
 * S20, QA ת61: the shop's contact details, one block wherever the site offers contact: the footer of every page, the
 * order page under "כתבו לנו" and "אין גישה", the cancellation and accessibility pages. It reads the build's config
 * (CONTACT_EMAIL, optionally CONTACT_PHONE: @hd/shared/contact, through web/src/copy.ts) and is not shown without it;
 * the lines around it are then in their wording without contact (site/copy/promises.he.json).
 */
import { contact } from '../copy';

export function ContactBlock({ title, class: cls }: { title?: string; class?: string }) {
  if (!contact) return null;
  return (
    <div class={`contact-block${cls ? ` ${cls}` : ''}`} data-contact="">
      {title ? <p class="contact-title">{title}</p> : null}
      <ul class="contact-list">
        <li>
          <span class="contact-label">אימייל: </span>
          <a href={`mailto:${contact.email}`} dir="ltr">
            {contact.email}
          </a>
        </li>
        {contact.phone && contact.phone_href ? (
          <li>
            <span class="contact-label">טלפון: </span>
            <a href={`tel:${contact.phone_href}`} dir="ltr" class="num">
              {contact.phone}
            </a>
          </li>
        ) : null}
      </ul>
    </div>
  );
}
