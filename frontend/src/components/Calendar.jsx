import React, {useState} from 'react';
import Icon from './Icon.jsx';

export function bookingDay(instant) {
  return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Riyadh',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(instant));
}
export function riyadhToday() {return bookingDay(new Date());}
export function bookingTime(instant,lang) {
  return new Intl.DateTimeFormat(lang==='ar'?'ar-SA':'en-GB',{timeZone:'Asia/Riyadh',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(instant));
}
function dateObject(value) {return new Date(`${value}T12:00:00Z`);}
function iso(date) {return `${date.getUTCFullYear()}-${String(date.getUTCMonth()+1).padStart(2,'0')}-${String(date.getUTCDate()).padStart(2,'0')}`;}

export default function Calendar({t,lang,admin=false,bookings=[],loading=false,error=null,onRetry,onCancel,cancelingId=null,notice=null}) {
  const [selected,setSelected]=useState(riyadhToday);
  const [month,setMonth]=useState(()=>dateObject(riyadhToday()));
  const locale=lang==='ar'?'ar-SA-u-ca-gregory':'en-GB';
  const format=(date,options)=>date.toLocaleDateString(locale,{...options,timeZone:'UTC'});
  const year=month.getUTCFullYear(),monthIndex=month.getUTCMonth();
  const start=new Date(Date.UTC(year,monthIndex,1,12));
  const days=new Date(Date.UTC(year,monthIndex+1,0,12)).getUTCDate();
  const move=delta=>setMonth(new Date(Date.UTC(year,monthIndex+delta,1,12)));
  const today=()=>{setSelected(riyadhToday());setMonth(dateObject(riyadhToday()));};
  const byDay={};
  for(const booking of bookings) (byDay[bookingDay(booking.start_at)]??=[]).push(booking);
  const details=(byDay[selected]??[]).slice().sort((a,b)=>a.start_at.localeCompare(b.start_at));
  return <>
    {notice&&<div className="notice" role="status">{notice}</div>}
    {error&&<div className="notice" role="alert">{error} {onRetry&&<button className="btn ghost" disabled={loading} onClick={onRetry}>{t('إعادة التحميل','Reload')}</button>}</div>}
    <div className="calendar-layout" aria-busy={loading}>
      <section className="calendar-panel">
        <div className="cal-header"><h2>{admin&&`${t('تقويم جميع الحجوزات','All bookings calendar')} · `}{format(month,{month:'long',year:'numeric'})}</h2><div className="cal-month-actions"><button className="btn ghost" onClick={today}>{t('اليوم','Today')}</button><button className="cal-arrow" aria-label={t('الشهر السابق','Previous month')} onClick={()=>move(-1)}>‹</button><button className="cal-arrow" aria-label={t('الشهر التالي','Next month')} onClick={()=>move(1)}>›</button></div></div>
        {loading&&<p className="tiny-note" role="status">{t('جارٍ تحميل الحجوزات…','Loading bookings…')}</p>}
        <div className="calendar-grid">
          {(lang==='ar'?['الأحد','الإثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت']:['Sun','Mon','Tue','Wed','Thu','Fri','Sat']).map(day=><div className="weekday" key={day}>{day}</div>)}
          {Array.from({length:Math.ceil((start.getUTCDay()+days)/7)*7},(_,index)=>{
            const day=index-start.getUTCDay()+1,date=new Date(Date.UTC(year,monthIndex,day,12)),value=iso(date);
            const events=byDay[value]??[];
            return <button key={value} data-date={value} aria-label={format(date,{dateStyle:'full'})} aria-pressed={value===selected} className={`day ${day<1||day>days?'other':''} ${value===riyadhToday()?'today':''} ${value===selected?'selected':''}`} onClick={()=>{setSelected(value);setMonth(date);}}><span className="day-num">{date.getUTCDate()}</span>{events.slice(0,2).map(booking=><span key={booking.booking_id} data-event-id={booking.booking_id} className={`day-event ${booking.status==='canceled'?'cancelled':''}`} title={booking.room_name[lang]}>{booking.room_name[lang]}</span>)}{events.length>2&&<span className="tiny-note">+{events.length-2}</span>}</button>;
          })}
        </div>
        <div className="legend"><span><i/>{t('حجز مؤكد','Confirmed')}</span><span><i className="cancelled"/>{t('حجز ملغى','Canceled')}</span></div>
      </section>
      <aside className="day-panel"><div className="overline">{admin?t('جميع الموظفين','ALL EMPLOYEES'):t('تفاصيل اليوم','DAY DETAILS')}</div><div className="side-heading">{t('حجوزات اليوم المحدد','Selected day bookings')}</div><div className="side-date">{format(dateObject(selected),{dateStyle:'long'})} · {t('توقيت الرياض','Asia/Riyadh')}</div>
        {details.map(booking=><div className="booking-item" key={booking.booking_id} data-detail-id={booking.booking_id}><span className={`status ${booking.status==='canceled'?'maintenance':''}`}>{booking.status==='confirmed'?t('مؤكد','Confirmed'):t('ملغى','Canceled')}</span><div style={{marginTop:10}}><b>{booking.room_name[lang]}</b></div><div className="booking-meta">{admin&&<><Icon name="users"/> {booking.employee_name[lang]}<br/></>}<Icon name="clock"/> <bdi>{bookingTime(booking.start_at,lang)} – {bookingTime(booking.end_at,lang)}</bdi><br/><Icon name="calendar"/> {format(dateObject(bookingDay(booking.start_at)),{dateStyle:'long'})}</div><div className="booking-actions"><span className="tiny-note"><bdi>{booking.booking_id}</bdi></span>{!admin&&booking.status==='confirmed'&&onCancel&&<button className="text-danger" disabled={cancelingId!==null} onClick={()=>onCancel(booking)}>{cancelingId===booking.booking_id?t('جارٍ الإلغاء…','Canceling…'):t('إلغاء الحجز','Cancel booking')}</button>}</div></div>)}
        {!details.length&&!loading&&!error&&<div className="empty"><Icon name="calendar" size="large"/>{t('لا توجد حجوزات في هذا اليوم','No bookings on this day')}</div>}
        <div className="side-caption">{t('اختيار اليوم للعرض فقط. جميع المواعيد بتوقيت الرياض.','Date selection is for viewing only. All booking times use Asia/Riyadh.')}</div>
      </aside>
    </div>
  </>;
}
