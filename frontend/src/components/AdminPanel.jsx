import React,{useEffect,useRef,useState} from 'react';
import Calendar from './Calendar.jsx';
import Icon from './Icon.jsx';
import {get,patch} from '../api.js';

export default function AdminPanel({t,lang}) {
  const [bookings,setBookings]=useState([]),[rooms,setRooms]=useState([]),[loading,setLoading]=useState(true);
  const [error,setError]=useState(null),[notice,setNotice]=useState(null),[changing,setChanging]=useState(null);
  const active=useRef(true),generation=useRef(0),writing=useRef(false);
  async function load() {
    const request=++generation.current;
    setLoading(true);setError(null);
    try {
      const [data,inventory]=await Promise.all([get('admin/bookings'),get('rooms')]);
      if(active.current&&request===generation.current) {setBookings(data);setRooms(inventory);}
    } catch {
      if(active.current&&request===generation.current) {setBookings([]);setRooms([]);setError('load');}
    } finally {if(active.current&&request===generation.current)setLoading(false);}
  }
  useEffect(()=>{active.current=true;load();return()=>{active.current=false;generation.current++;};},[]);
  async function change(room) {
    if(writing.current) return;
    writing.current=true;setChanging(room.id);setNotice(null);setError(null);
    try {
      const updated=await patch(`admin/rooms/${encodeURIComponent(room.id)}/status`,{status:room.status==='maintenance'?'available':'maintenance'});
      if(active.current) {setRooms(previous=>previous.map(item=>item.id===updated.id?updated:item));setNotice('updated');}
    } catch {
      await load();
      if(active.current) setError('status');
    } finally {writing.current=false;if(active.current)setChanging(null);}
  }
  return <>
    <div className="page-top"><div><div className="overline">{t('لوحة منفصلة للمسؤول','SEPARATE MANAGER SPACE')}</div><h1>{t('إدارة القاعات.','Room management.')}</h1><p>{t('تقويم لجميع الحجوزات، وإدارة بسيطة لحالة القاعات والصيانة.','A calendar of all bookings and simple room maintenance controls.')}</p></div><button className="btn ghost" disabled={loading||changing!==null} onClick={load}>{t('تحديث البيانات','Refresh data')}</button></div>
    <div className="admin-intro"><Icon name="info"/>{t('اختيار الدور للتجربة فقط — لا توجد مصادقة حقيقية.','Demo-only role selection — not a secure login.')}</div>
    <div className="admin-stats"><div className="stat"><strong>{loading||error==='load'?'—':rooms.length}</strong><span>{t('إجمالي القاعات','Total rooms')}</span></div><div className="stat"><strong>{loading||error==='load'?'—':bookings.filter(item=>item.status==='confirmed').length}</strong><span>{t('الحجوزات المؤكدة','Confirmed bookings')}</span></div><div className="stat"><strong>{loading||error==='load'?'—':rooms.filter(room=>room.status==='maintenance').length}</strong><span>{t('قاعات تحت الصيانة','Rooms under maintenance')}</span></div></div>
    <Calendar t={t} lang={lang} admin bookings={bookings} loading={loading} onRetry={load} error={error==='status'?t('لم يتأكد رد تغيير الحالة. راجعي البيانات المحدثة قبل إعادة المحاولة.','Status response was not verified. Check the refreshed inventory before retrying.'):error?t('تعذر تحميل بيانات المسؤول. حاولي مجددًا.','Manager data could not load. Please retry.'):null} notice={notice?t('حالة القاعة محدثة ومتحقق منها. الحجوزات السابقة محفوظة.','Room status verified. Existing bookings are preserved.'):null}/>
    <section className="rooms-panel admin-rooms-section"><h2 className="section-mini-heading">{t('حالة القاعات','Room status')}</h2><p className="tiny-note">{t('بيانات القاعات مقروءة من Firestore.','Room inventory read from Firestore.')}</p><div className="room-admin-grid">{rooms.map(room=><div className="room-admin" key={room.id} data-room-id={room.id}><strong>{room.name[lang]}</strong><small>{room.capacity} {t('مقعد','seats')} · {room.type==='training'?t('تدريب','Training'):t('اجتماعات','Meeting')}</small><button className={room.status==='maintenance'?'on-maint':''} disabled={loading||changing!==null} onClick={()=>change(room)}>{changing===room.id?t('جارٍ الحفظ…','Saving…'):room.status==='maintenance'?t('تحت الصيانة · إعادة الإتاحة','Maintenance · Restore'):t('متاحة · وضع صيانة','Available · Set maintenance')}</button></div>)}</div><div className="warn-note">{t('الصيانة تمنع الحجوزات الجديدة ولا تلغي الحجوزات السابقة.','Maintenance blocks new bookings and does not cancel existing bookings.')}</div></section>
  </>;
}
