import React, {useEffect,useState,useRef} from 'react';
import {get,post} from './api.js';
import Icon from './components/Icon.jsx';
import ChatPanel from './components/ChatPanel.jsx';
import MyBookings from './components/MyBookings.jsx';
import AdminPanel from './components/AdminPanel.jsx';

export default function App() {
  const [lang,setLang]=useState('ar'),[theme,setTheme]=useState('light');
  const [role,setRole]=useState('employee'),[view,setView]=useState('chat');
  const [employee,setEmployee]=useState('sara'),[drafts,setDrafts]=useState({});
  const [chats,setChats]=useState({});
  const [chatBusy,setChatBusy]=useState(false);
  const sending=useRef(false);
  const [health,setHealth]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(false);
  const [employees,setEmployees]=useState(null);
  const t=(ar,en)=>lang==='ar'?ar:en;
  useEffect(()=>{document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.body.classList.toggle('dark',theme==='dark');},[lang,theme]);
  async function switchEmployee(next) {
    if(sending.current || next===employee) return;
    const current=chats[employee];
    if(current?.session_id) {
      sending.current=true;setChatBusy(true);
      try {
        const result=await post('chat',{employee_id:employee,session_id:current.session_id,message:'Discard pending offer',language:lang,action:'discard_offer'});
        if(result.status==='unknown') {
          setChats(prev=>({...prev,[employee]:{...prev[employee],error:result.reply}}));
          return;
        }
        setChats(prev=>({...prev,[employee]:{...prev[employee],pending_offer:null,options:[]}}));
      } catch(error) {
        if(error.status!==409) {
          setChats(prev=>({...prev,[employee]:{...prev[employee],error:t('تعذر إغلاق العرض السابق. تحققي من الاتصال قبل تبديل الموظف.','Could not clear the previous offer. Check the connection before switching employee.')}}));
          return;
        }
        setChats(prev=>({...prev,[employee]:{...prev[employee],session_id:null,pending_offer:null,options:[]}}));
      } finally {sending.current=false;setChatBusy(false);}
    }
    setEmployee(next);
  }
  async function send(message,offerId=null,roomId=null) {
    const content=message.trim();
    if(sending.current || (!content&&!offerId) || !employees?.some(p=>p.id===employee)) return;
    const owner=employee;
    const current=chats[owner]??{messages:[]};
    sending.current=true;setChatBusy(true);
    setChats(prev=>({...prev,[owner]:{...current,error:null,messages:[...(current.messages??[]),{who:'user',text:content}]}}));
    setDrafts(prev=>({...prev,[owner]:''}));
    try {
      const payload={employee_id:owner,session_id:current.session_id??null,language:lang};
      const result=await post(offerId?'bookings/confirm':'chat',offerId?{...payload,offer_id:offerId}:{...payload,message:content,...(roomId?{action:'select_room',room_id:roomId}:{})});
      setChats(prev=>({...prev,[owner]:{...result,messages:[...(prev[owner]?.messages??[]),{who:'bot',text:result.reply}],error:null}}));
    } catch(error) {
      setChats(prev=>({...prev,[owner]:{...prev[owner],...(error.status===409?{session_id:null,pending_offer:null,options:[]}:{}),error:error.status===409?t('انتهت الجلسة. أرسلي الطلب مجددًا؛ لم يتم تأكيد حجز جديد.','Session expired. Send your request again; no new booking is confirmed.'):t('تعذرت الاستجابة. إذا كنت تؤكدين عرضًا فأعيدي تأكيد العرض نفسه بأمان، ولا تبدئي طلبًا مكررًا.','Response unavailable. If confirming, retry the same offer safely instead of starting a duplicate request.')}}));
    } finally {sending.current=false;setChatBusy(false);}
  }
  async function refresh() {
    setBusy(true);setError(false);
    const results=await Promise.allSettled([get('health'),get('employees')]);
    setHealth(results[0].status==='fulfilled'?results[0].value:null);
    setError(results.some(result=>result.status==='rejected'));
    const people=results[1].status==='fulfilled'?results[1].value:null;
    setEmployees(people);
    if(people?.length) setEmployee(current=>people.some(p=>p.id===current)?current:people[0].id);
    setBusy(false);
  }
  useEffect(()=>{refresh();},[]);
  const people=employees??[];
  
  return <div className="app"><header className="site-header"><div className="header-content"><div className="brand"><span className="brand-mark"><Icon size="large"/></span><bdi>MeetSpace<span className="brand-dot">.</span></bdi></div><nav className="main-nav" aria-label={t('التنقل','Navigation')}>{role==='employee'?<><button className={`nav-btn ${view==='chat'?'active':''}`} onClick={()=>setView('chat')}><Icon/>{t('المساعد الذكي','AI assistant')}</button><button className={`nav-btn ${view==='calendar'?'active':''}`} onClick={()=>setView('calendar')}><Icon name="calendar"/>{t('تقويم حجوزاتي','My calendar')}</button></>:<span className="nav-btn active"><Icon name={role==='admin'?'shield':'users'}/>{role==='admin'?t('مسؤول القاعات','Room manager'):t('اختيار طريقة الدخول','Choose your experience')}</span>}</nav><div className="header-actions"><button className="icon-button" aria-label={t('تغيير النمط','Toggle theme')} onClick={()=>setTheme(theme==='light'?'dark':'light')}><Icon name={theme==='light'?'moon':'sun'}/></button><button className="icon-button" aria-label={t('تغيير اللغة','Switch language')} onClick={()=>setLang(lang==='ar'?'en':'ar')}><Icon name="globe"/></button>{role==='employee'&&<div className="avatar-group"><span className="avatar"><Icon name="users" size="small"/></span><select aria-label={t('الموظف','Employee')} value={employee} disabled={chatBusy} onChange={e=>switchEmployee(e.target.value)}>{people.map(p=><option key={p.id} value={p.id}>{p.display_name?.[lang]??p[lang]}</option>)}</select></div>}<button className="role-switch" aria-label={t('تبديل الدور','Switch role')} onClick={()=>setRole('choose')}><Icon name="logout"/>{t('تبديل الدور','Switch role')}</button></div></div></header><main className="container"><div className="notice connection-bar" role="status"><span>{t('المرحلة الثالثة','Milestone 3')} · API: {busy?'…':health?'OK':t('غير متصل','unavailable')} · Ollama: {health?.ollama.status??'—'} · Firestore: {health?.firestore.status??'—'}</span><button className="btn ghost" disabled={busy} onClick={refresh}>{t('فحص الاتصال','Check connections')}</button>{!employees?.length&&<span>{t('تعذر تحميل قائمة الموظفين من Firestore.','Firestore employee list is not loaded.')}</span>}{error&&<span>{t('تعذر تحميل بعض البيانات. راجعي إعداد الخادم والاتصال.','Some data could not load. Check backend configuration and connectivity.')}</span>}</div>{role==='choose'?<div className="role-wrapper"><div className="overline">{t('مرحبًا في MeetSpace','WELCOME TO MEETSPACE')}</div><h1>{t('كيف تبغين تستخدمين MeetSpace؟','How would you like to enter?')}</h1><p>{t('واجهتان مستقلتان تمامًا. اختاري تجربة الموظف أو مسؤول القاعات.','Two separate experiences. Choose employee or room manager.')}</p><div className="role-cards">{[['employee','مساحة الموظف','Employee experience','احجزي القاعات مع المساعد الذكي، وشوفي حجوزاتك على التقويم.','Book through the assistant and view your calendar.'],['admin','مساحة مسؤول القاعات','Room manager experience','شاهدي جميع الحجوزات وتابعي حالة القاعات.','View all bookings and room statuses.']].map(([id,ar,en,descAr,descEn])=><button key={id} className={`role-card ${id==='admin'?'admin-role':''}`} onClick={()=>{setRole(id);setView('chat');}}><span className="role-symbol"><Icon name={id==='admin'?'shield':'spark'} size="large"/></span><h2>{t(ar,en)}</h2><p>{t(descAr,descEn)}</p><span className="link">{t('الدخول','Enter')} <Icon name="arrow"/></span></button>)}</div><p className="tiny-note">{t('اختيار الدور للتجربة فقط — لا توجد مصادقة حقيقية.','Demo-only role selection — not a secure login.')}</p></div>:role==='admin'?<AdminPanel t={t} lang={lang}/>:view==='calendar'?<MyBookings key={employee} employeeId={employee} t={t} lang={lang} onChat={()=>setView('chat')}/>:<ChatPanel t={t} lang={lang} chat={chats[employee]??{messages:[]}} loading={chatBusy} connected={!!employees?.some(p=>p.id===employee)} onSend={send} draft={drafts[employee]??''} onDraft={value=>setDrafts(prev=>({...prev,[employee]:value}))}/>}</main><footer className="footer"><span>MeetSpace © 2026 · {t('مساعد الحجز المحلي','Local booking assistant')}</span><span>{t('الحجز بالمحادثة · تقويم الحجوزات · إدارة القاعات','Chat booking · Booking calendars · Room management')}</span></footer></div>;
}
