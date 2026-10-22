import React,{useEffect,useRef,useState} from 'react';
import Calendar,{bookingDay,bookingTime} from './Calendar.jsx';
import Icon from './Icon.jsx';
import {get,post} from '../api.js';

export default function MyBookings({t,lang,employeeId,onChat}) {
  const [bookings,setBookings]=useState([]),[loading,setLoading]=useState(true);
  const [error,setError]=useState(null),[notice,setNotice]=useState(null),[cancelingId,setCancelingId]=useState(null);
  const active=useRef(true),generation=useRef(0),canceling=useRef(false);
  async function load() {
    const request=++generation.current;
    setLoading(true);setError(null);
    try {
      const data=await get(`bookings?employee_id=${encodeURIComponent(employeeId)}`);
      if(active.current&&request===generation.current) setBookings(data.filter(item=>item.employee_id===employeeId));
    } catch {
      if(active.current&&request===generation.current) {setBookings([]);setError('load');}
    } finally {if(active.current&&request===generation.current) setLoading(false);}
  }
  useEffect(()=>{active.current=true;load();return()=>{active.current=false;generation.current++;};},[employeeId]);
  async function cancel(booking) {
    if(canceling.current) return;
    const question=t('تأكيد إلغاء الحجز؟','Confirm cancellation?')+`\n${booking.room_name[lang]} · ${bookingDay(booking.start_at)} · ${bookingTime(booking.start_at,lang)}–${bookingTime(booking.end_at,lang)}`;
    if(!window.confirm(question)) return;
    canceling.current=true;setCancelingId(booking.booking_id);setNotice(null);setError(null);
    try {
      const updated=await post(`bookings/${encodeURIComponent(booking.booking_id)}/cancel`,{employee_id:employeeId,confirmed:true});
      if(active.current) {
        setBookings(previous=>previous.map(item=>item.booking_id===updated.booking_id?updated:item));
        setNotice('canceled');
      }
    } catch {
      // Re-read after an uncertain response; never show an optimistic success.
      await load();
      if(active.current) setError('cancel');
    } finally {canceling.current=false;if(active.current)setCancelingId(null);}
  }
  return <><div className="page-top"><div><div className="overline">{t('مساحة الموظف','EMPLOYEE AREA')}</div><h1>{t('حجوزاتك، بلمحة واحدة.','Your bookings, at a glance.')}</h1><p>{t('كل مواعيدك في تقويم واضح، وتفاصيل الحجز تظهر عند اختيار اليوم.','See your bookings in one calendar and select a date for details.')}</p></div><div className="cal-month-actions"><button className="btn ghost" disabled={loading||cancelingId!==null} onClick={load}>{t('تحديث الحجوزات','Refresh bookings')}</button><button className="btn" onClick={onChat}><Icon name="plus"/>{t('حجز جديد','New booking')}</button></div></div><Calendar t={t} lang={lang} bookings={bookings} loading={loading} error={error==='cancel'?t('لم يتأكد رد الإلغاء. راجعي الحالة المحدثة قبل إعادة المحاولة.','Cancellation response was not verified. Check the refreshed status before retrying.'):error?t('تعذر تحميل الحجوزات. حاولي مجددًا.','Bookings could not load. Please retry.'):null} onRetry={load} onCancel={cancel} cancelingId={cancelingId} notice={notice?t('تم إلغاء الحجز وتحرير فترة القاعة بعد التحقق من الحفظ.','Cancellation and released interval verified in Firestore.'):null}/></>;
}
