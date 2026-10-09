export function NotFound() {
  return (
    <div class="wrap page">
      <div class="page-head">
        <h1 tabIndex={-1}>הדף לא נמצא</h1>
        <p class="muted">ייתכן שהקישור ישן, או שהמוצר כבר לא מוצג.</p>
      </div>
      <p>
        <a class="btn btn-primary" href="/">
          לדף הבית
        </a>
      </p>
    </div>
  );
}
