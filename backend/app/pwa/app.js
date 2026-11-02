'use strict';
// Authentication token is intentionally kept only in memory; no student data in localStorage,
// IndexedDB, CacheStorage or the service worker. Reloading requires reauthentication.
const s={token:null,user:null,classes:[],types:[],page:'home',revision:0,filters:{},busy:false,student:null,installEvent:null};
const $=id=>document.getElementById(id);
// Display the two authentic internal logos only after their files are installed.
// The third logo belongs exclusively to the installed PWA / Android launcher icon.
for (const img of document.querySelectorAll('[data-brand-image]')) {
  const ready = () => { if (img.naturalWidth > 0) img.parentElement.classList.add('has-logo'); };
  img.addEventListener('load', ready);
  img.addEventListener('error', () => img.parentElement.classList.remove('has-logo'));
  if (img.complete) ready();
}

const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const fmtInt=n=>new Intl.NumberFormat('vi-VN').format(Number(n)||0);
const today=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const qs=obj=>new URLSearchParams(Object.entries(obj).filter(([,v])=>v!==undefined&&v!==null&&String(v)!=='').map(([k,v])=>[k,String(v)])).toString();
const setBusy=(button,busy,text)=>{if(!button)return;button.disabled=busy;if(text)button.textContent=text};
const toast=(message,fail=false)=>{const x=$('toast');x.textContent=message;x.classList.toggle('fail',fail);x.classList.remove('hidden');clearTimeout(toast.timer);toast.timer=setTimeout(()=>x.classList.add('hidden'),5200)};
function setOnline(ok){$('syncState').textContent=ok?'Đã kết nối':'Lỗi kết nối';$('syncState').classList.toggle('fail',!ok)}
async function api(path,{method='GET',body,key}={}){
 if(!s.token)throw new Error('Bạn chưa đăng nhập');
 const headers={'Accept':'application/json','Authorization':'Bearer '+s.token};
 if(body!==undefined)headers['Content-Type']='application/json';
 if(key)headers['Idempotency-Key']=key;
 let response;
 try{response=await fetch(path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});}catch(_){setOnline(false);throw new Error('Không kết nối được máy chủ. Kiểm tra Internet và thử lại.');}
 setOnline(true);
 if(response.status===401){logout();throw new Error('Phiên đăng nhập không còn hiệu lực. Vui lòng đăng nhập lại.');}
 if(!response.ok){let detail;try{const p=await response.json();detail=p.detail;}catch(_){}throw new Error(typeof detail==='string'?detail:'Máy chủ phản hồi lỗi '+response.status)}
 if(response.status===204)return null;
 return response.json();
}
// Evidence images are always sent with the active authenticated session.
// No bearer tokens in URLs and no student photos cached in browser storage.
async function uploadEvidence(violationId, file){
 if(!s.token)throw new Error('Phiên đăng nhập đã hết hạn');
 if(file.size>8*1024*1024)throw new Error('Ảnh phải nhỏ hơn 8 MB');
 if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw new Error('Chỉ nhận JPG, PNG, WEBP');
 const body=new FormData();body.append('file',file,file.name||'evidence.jpg');
 let response;
 try{response=await fetch(`/violations/${violationId}/photos`,{method:'POST',headers:{Authorization:'Bearer '+s.token},body,cache:'no-store'});}
 catch(_){throw new Error('Mất kết nối khi gửi ảnh, hãy bấm thử lại.');}
 let payload={};try{payload=await response.json()}catch(_){}
 if(!response.ok)throw new Error(typeof payload.detail==='string'?payload.detail:'Không thể lưu ảnh '+response.status);
 return payload;
}
async function viewEvidence(violation){
 const photos=violation.photos||[];if(!photos.length){toast('Bản ghi không có ảnh minh chứng',true);return;}
 const urls=[];
 try{
  $('dialogContent').replaceChildren();
  const heading=document.createElement('h2');heading.textContent=`Ảnh minh chứng #${violation.id}`;$('dialogContent').appendChild(heading);
  for(const photo of photos){
   const response=await fetch(`/violations/${violation.id}/photos/${photo.id}`,{headers:{Authorization:'Bearer '+s.token},cache:'no-store'});
   if(!response.ok)throw new Error('Không có quyền xem ảnh hoặc máy chủ bị lỗi');
   const blob=await response.blob();const url=URL.createObjectURL(blob);urls.push(url);
   const img=document.createElement('img');img.src=url;img.alt='Ảnh minh chứng';img.loading='lazy';img.style.cssText='width:100%;max-height:65vh;object-fit:contain;margin:8px 0;border-radius:8px';
   $('dialogContent').appendChild(img);
  }
  $('detailDialog').showModal();
  $('detailDialog').addEventListener('close',()=>urls.forEach(x=>URL.revokeObjectURL(x)),{once:true});
 }catch(e){urls.forEach(x=>URL.revokeObjectURL(x));toast(e.message,true)}
}
async function addEvidenceLater(violation){
 // Allows staff to recover from a previously interrupted image upload.
 const input=document.createElement('input');input.type='file';input.accept='image/jpeg,image/png,image/webp';
 input.multiple=true;input.style.display='none';document.body.appendChild(input);
 input.addEventListener('change',async()=>{
  try{
   const files=Array.from(input.files||[]);if(files.length+(violation.photo_count||0)>3)throw new Error('Mỗi vi phạm tối đa 3 ảnh');
   for(const file of files)await uploadEvidence(violation.id,file);
   if(files.length){toast('Đã bổ sung ảnh minh chứng.');navigate('journal');}
  }catch(e){toast(e.message,true)}finally{input.remove();}
 },{once:true});input.click();
}
async function logIn(event){event.preventDefault();const b=$('loginButton');setBusy(b,true,'Đang đăng nhập…');try{
 const response=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:$('username').value.trim(),password:$('password').value}),cache:'no-store'});
 const payload=await response.json();if(!response.ok)throw new Error(payload.detail||'Đăng nhập thất bại');
 s.token=payload.access_token;$('password').value='';s.user=await api('/auth/me');
 const [classes,types]=await Promise.all([api('/classes'),api('/violation-types')]);s.classes=classes;s.types=types;
 $('loginScreen').classList.add('hidden');$('appShell').classList.remove('hidden');renderNav();navigate('home');
 }catch(err){if(s.token)logout();toast(err.message||'Không thể đăng nhập',true)}finally{setBusy(b,false,'Đăng nhập')}}
function logout(){s.token=null;s.user=null;s.classes=[];s.types=[];s.student=null;$('appShell').classList.add('hidden');$('loginScreen').classList.remove('hidden');$('pageContent').replaceChildren();$('password').value='';}
const tabs=[['home','⌂','Trang chủ'],['record','✎','Nhập vi phạm'],['search','⌕','Tra cứu'],['warnings','⚑','Cảnh báo'],['reports','▤','Báo cáo'],['journal','≡','Nhật ký'],['admin','⚙','Quản trị']];
function renderNav(){for(const [id,el] of [['desktopNav',true],['bottomNav',false]]){
 $(id).innerHTML=tabs.filter(([key])=>el?(key!=='admin'||s.user?.role==='admin'):['home','record','search','warnings','reports'].includes(key)).map(([key,symbol,title])=>`<button type="button" data-nav="${key}" class="${s.page===key?'active':''} ${el?'nav-btn':''}"><span class="symbol" aria-hidden="true">${symbol}</span><span>${escapeHTML(el?title:(key==='record'?'Nhập':title))}</span></button>`).join('');
 $(id).querySelectorAll('[data-nav]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.nav)));
 }$('userInfo').textContent=`${s.user?.display_name||''} · ${s.user?.role||''}`;}
async function navigate(name){if(!s.token)return;s.page=name;s.revision++;let version=s.revision;renderNav();const title=tabs.find(t=>t[0]===name)?.[2]||'Trang chủ';$('pageTitle').textContent=title;$('pageContent').innerHTML='<div class="loader">Đang tải dữ liệu…</div>';
 try{switch(name){case 'home':await renderHome(version);break;case 'record':await renderRecord(version);break;case 'search':await renderSearch(version);break;case 'warnings':await renderWarnings(version);break;case 'reports':await renderReports(version);break;case 'journal':await renderJournal(version);break;case 'admin':await renderAdmin(version);break;default:await renderHome(version);}}
 catch(e){if(version===s.revision){$('pageContent').innerHTML=`<div class="notice danger-notice">${escapeHTML(e.message)}</div>`;toast(e.message,true)}}}
const current=(v)=>v===s.revision;
const safeOptions=(list,valueKey,textKey,selected)=>list.map(item=>`<option value="${escapeHTML(item[valueKey])}" ${String(item[valueKey])===String(selected)?'selected':''}>${escapeHTML(item[textKey])}</option>`).join('');
const classSelect=(id,selected='',allLabel='Tất cả lớp')=>`<select id="${id}"><option value="">${escapeHTML(allLabel)}</option>${safeOptions(s.classes,'id','name',selected)}</select>`;
const typeSelect=(id,selected='',allLabel='Tất cả loại')=>`<select id="${id}"><option value="">${escapeHTML(allLabel)}</option>${safeOptions(s.types,'id','name',selected)}</select>`;
const warningTag=w=>`<span class="tag ${w==='Cảnh báo cao'?'high':w==='Cảnh báo'||w==='Cần quan tâm'?'warn':w==='Tốt'?'good':'info'}">${escapeHTML(w)}</span>`;
const empty=(message='Chưa có dữ liệu phù hợp')=>`<div class="empty">${escapeHTML(message)}</div>`;
function wireStudentLinks(root=$('pageContent')){root.querySelectorAll('[data-student]').forEach(b=>b.addEventListener('click',()=>showStudent(b.dataset.student)))}
async function showStudent(code){try{const p=await api('/students/'+encodeURIComponent(code));const v=p.history||[];
 $('dialogContent').innerHTML=`<div class="eyebrow">HỒ SƠ HỌC SINH</div><h2>${escapeHTML(p.full_name)}</h2><p class="muted">Mã học sinh ${escapeHTML(p.code)} · Lớp ${escapeHTML(p.class_name)} · ${escapeHTML(p.birth_date)} · ${escapeHTML(p.gender)}</p><div class="row">${warningTag(p.warning)} <strong>${fmtInt(p.total)} lượt vi phạm</strong></div><p class="notice">${escapeHTML(p.recommendation||'Không có đề nghị')}</p><h3>Nhật ký vi phạm</h3>${v.length?`<div class="list-cards">${v.map(x=>`<div class="list-card"><div class="item-title">${escapeHTML(x.violation_type)}</div><div class="sub">${escapeHTML(x.happened_on)} · Người ghi: ${escapeHTML(x.recorder)}</div>${x.note?`<div class="sub">${escapeHTML(x.note)}</div>`:''}${x.photo_count?`<button class="pill-button" data-view-photo="${x.id}">Xem ${x.photo_count} ảnh</button>`:''}</div>`).join('')}</div>`:empty('Học sinh chưa có lượt vi phạm nào.')}`;
 $('dialogContent').querySelectorAll('[data-view-photo]').forEach(b=>b.onclick=()=>{const item=v.find(x=>x.id===Number(b.dataset.viewPhoto));$('detailDialog').close();if(item)viewEvidence(item);});
 $('detailDialog').showModal();}catch(e){toast(e.message,true)}}
async function renderHome(v){const d=await api('/dashboard');if(!current(v))return;
 const cards=[['Vi phạm hôm nay',d.today_total,'today'],['Đi học muộn hôm nay',d.today_late,'late'],['Nghỉ không phép hôm nay',d.today_absent,'absent'],['Tổng lượt ghi nhận',d.all_total,'all']];
 const types=Object.entries(d.by_type||{});const max=Math.max(1,...types.map(x=>x[1]));
 const rows=(d.by_class||[]).slice().sort((a,b)=>(b.total||0)-(a.total||0)).slice(0,12);
 $('pageContent').innerHTML=`<div class="section-head"><div><h3>Tổng quan toàn trường</h3><div class="hint">Dữ liệu lấy trực tiếp từ nhật ký · Hôm nay ${escapeHTML(d.today)}</div></div><button id="gotoJournal" class="secondary">Xem nhật ký</button></div>
 <div class="cards">${cards.map(([name,value,key])=>`<button class="stat-card clickable" data-kpi="${key}"><div class="kpi-label">${escapeHTML(name)}</div><div class="kpi-value">${fmtInt(value)}</div><div class="hint">Nhấn để xem chi tiết →</div></button>`).join('')}</div>
 <div class="two-col"><section class="panel"><h3>Thống kê theo loại</h3>${types.length?types.map(([name,num])=>`<div class="bar-row"><span>${escapeHTML(name)}</span><progress class="bar-progress" max="${max}" value="${num}"></progress><strong>${fmtInt(num)}</strong></div>`).join(''):empty()}</section>
 <section class="panel"><h3>Lớp có nhiều lượt vi phạm</h3>${rows.length?`<div class="table-wrap"><table><thead><tr><th>Lớp</th><th>Tổng lượt</th><th>Chi tiết</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${escapeHTML(x.class_name)}</td><td><b>${fmtInt(x.total)}</b></td><td><button class="pill-button" data-class-summary="${x.class_id}">Xem lớp</button></td></tr>`).join('')}</tbody></table></div>`:empty()}</section></div>
 <div class="notice">Số liệu đồng bộ từ máy chủ. Các thiết bị đang mở sẽ kiểm tra cập nhật định kỳ; bạn cũng có thể nhấn “Làm mới”. Không lưu dữ liệu học sinh trong bộ nhớ offline của trình duyệt.</div>`;
 $('gotoJournal').onclick=()=>navigate('journal');
 $('pageContent').querySelectorAll('[data-kpi]').forEach(b=>b.onclick=()=>{let key=b.dataset.kpi;s.filters.journal={...(key==='today'?{start:d.today,end:d.today}:{}),...(key==='late'?{start:d.today,end:d.today,type_id:s.types.find(t=>t.name==='Đi học muộn')?.id}:{}),...(key==='absent'?{start:d.today,end:d.today,type_id:s.types.find(t=>t.name==='Nghỉ học không phép')?.id}:{})};navigate('journal')});
 $('pageContent').querySelectorAll('[data-class-summary]').forEach(b=>b.onclick=()=>showClassSummary(Number(b.dataset.classSummary)));
}
async function showClassSummary(id){try{const d=await api('/classes/'+id+'/summary');$('dialogContent').innerHTML=`<h2>Thống kê lớp ${escapeHTML(d.class_name)}</h2><div class="row"><span class="tag info">Sĩ số: ${fmtInt(d.headcount)}</span><span class="tag">${fmtInt(d.students_with_violations)} HS vi phạm</span><span class="tag warn">${fmtInt(d.total)} lượt</span><span class="tag high">${fmtInt(d.severe_total)} nghiêm trọng</span></div><p class="hint">${fmtInt(d.different_types)} loại đã phát sinh / ${fmtInt(d.configured_types)} loại cấu hình</p><div class="table-wrap"><table><thead><tr><th>Học sinh</th><th>Lượt</th><th>Mức</th></tr></thead><tbody>${d.students.map(x=>`<tr><td>${escapeHTML(x.full_name)}</td><td>${fmtInt(x.total)}</td><td>${warningTag(x.warning)}</td></tr>`).join('')}</tbody></table></div>`;$('detailDialog').showModal()}catch(e){toast(e.message,true)}}
async function renderRecord(v){if(!s.user||!['admin','recorder'].includes(s.user.role)){$('pageContent').innerHTML='<div class="notice">Tài khoản này chỉ có quyền theo dõi. Không được nhập vi phạm.</div>';return;}
 const now=today();$('pageContent').innerHTML=`<div class="panel"><h3>Ghi nhận vi phạm mới</h3><p class="hint">Chọn đúng học sinh và loại vi phạm. Thời gian ghi nhận được máy chủ cố định khi lưu.</p><form id="recordForm" class="stack">
 <div class="fields"><label>Lọc theo lớp ${classSelect('recordClass','', 'Chọn lớp để lọc')}</label><label>Tìm học sinh<input id="studentQuery" type="search" placeholder="Nhập họ tên hoặc mã học sinh" autocomplete="off"></label></div>
 <label>Học sinh <select id="studentChoice" required><option value="">Đang tải danh sách…</option></select></label><p id="studentSummary" class="hint">Chưa chọn học sinh.</p>
 <div class="fields"><label>Loại vi phạm <select id="recordType" required><option value="">Chọn loại vi phạm</option>${safeOptions(s.types,'id','name')}</select></label><label>Ngày xảy ra<input type="date" id="recordDate" required value="${now}"></label></div>
 <label>Ghi chú (không bắt buộc)<textarea id="recordNote" maxlength="2000" placeholder="Ghi rõ tình huống, nếu cần"></textarea></label>
 <div class="fields"><label>Chụp ảnh bằng camera<input id="recordCamera" type="file" accept="image/*" capture="environment"></label><label>Chọn ảnh từ máy (tối đa 3)<input id="recordPhotos" type="file" accept="image/jpeg,image/png,image/webp" multiple></label></div>
 <p id="recordPhotoStatus" class="hint">Ảnh chỉ tải lên sau khi lưu vi phạm.</p><button class="primary full" id="saveRecord" type="submit">Lưu vi phạm</button><div class="notice">Mỗi lần nhấn Lưu dùng một khóa chống gửi trùng. Khi mạng mất trong lúc lưu, hãy kiểm tra nhật ký trước khi thực hiện thao tác mới.</div></form></div>`;
 let selected=null;let pendingKey=null;let lastPayload=null;let pendingViolation=null;let sentPhotos=0;let uncertain=false;let requestCounter=0;
 async function loadChoices(){const my=++requestCounter;let parameters={q:$('studentQuery').value.trim(),class_id:$('recordClass').value,limit:100};
 const p=await api('/students?'+qs(parameters));if(my!==requestCounter||!current(v))return;
 const select=$('studentChoice');select.innerHTML=`<option value="">Chọn học sinh (${p.total} kết quả${p.total>100?' – hiển thị 100':''})</option>`+p.items.map(x=>`<option value="${escapeHTML(x.code)}">${escapeHTML(x.full_name)} · ${escapeHTML(x.class_name)} (${escapeHTML(x.code)})</option>`).join('');
 if(selected&&p.items.some(x=>x.code===selected))select.value=selected;else selected=null;
 select.onchange=()=>{selected=select.value;const st=p.items.find(x=>x.code===selected);$('studentSummary').textContent=st?`${st.full_name} · ${st.class_name} · Mã ${st.code}`:'Chưa chọn học sinh.'};
 }
 $('recordClass').onchange=()=>loadChoices().catch(e=>toast(e.message,true));
 let debounce;$('studentQuery').oninput=()=>{clearTimeout(debounce);debounce=setTimeout(()=>loadChoices().catch(e=>toast(e.message,true)),280)};
 await loadChoices();
 $('recordForm').onsubmit=async event=>{event.preventDefault();const code=$('studentChoice').value;const type=Number($('recordType').value);
 if(!code||!type){toast('Chọn học sinh và loại vi phạm.',true);return}
 const payload={student_code:code,violation_type_id:type,happened_on:$('recordDate').value,note:$('recordNote').value.trim()};
 const serialized=JSON.stringify(payload);
 if(!pendingViolation&&serialized!==lastPayload){pendingKey=crypto.randomUUID();lastPayload=serialized;}
 const b=$('saveRecord');setBusy(b,true,'Đang lưu…');
 try{
  if(!pendingViolation){uncertain=true;pendingViolation=await api('/violations',{method:'POST',body:payload,key:pendingKey});}
  const files=[...Array.from($('recordCamera').files||[]),...Array.from($('recordPhotos').files||[])];
  if(files.length>3)throw new Error('Mỗi vi phạm chỉ được chọn tối đa 3 ảnh. Bản ghi vi phạm đã lưu, có thể bổ sung ảnh trong Nhật ký.');
  $('recordPhotoStatus').textContent=`Đã lưu vi phạm #${pendingViolation.id}. Ảnh đã gửi: ${sentPhotos}/${files.length}.`;
  for(let i=sentPhotos;i<files.length;i++){
   await uploadEvidence(pendingViolation.id,files[i]);sentPhotos=i+1;
   $('recordPhotoStatus').textContent=`Đã gửi ${sentPhotos}/${files.length} ảnh minh chứng.`;
  }
  pendingViolation=null;sentPhotos=0;pendingKey=null;lastPayload=null;uncertain=false;
  toast('Đã lưu vi phạm và ảnh lên máy chủ.');$('recordNote').value='';$('recordType').value='';
  $('recordCamera').value='';$('recordPhotos').value='';$('recordPhotoStatus').textContent='Chưa chọn ảnh.';
 }catch(e){toast(e.message,true);
  if(!pendingViolation && !e.message.includes('Không kết nối') && !e.message.includes('Mất kết nối'))uncertain=false;
  if(pendingViolation){$('recordPhotoStatus').textContent=`Bản ghi #${pendingViolation.id} đã lưu. Ảnh gửi được ${sentPhotos} tệp. Bấm Lưu để tiếp tục, không cần tạo vi phạm mới.`;}
 }finally{setBusy(b,false,pendingViolation?'Tiếp tục gửi ảnh':'Lưu vi phạm');
  const locked=Boolean(pendingViolation)||uncertain;
  for(const id of ['recordClass','studentQuery','studentChoice','recordType','recordDate','recordNote','recordCamera','recordPhotos'])$(id).disabled=locked;
 }};
}
async function renderSearch(v){const prev=s.filters.search||{};
 $('pageContent').innerHTML=`<section class="panel"><h3>Tra cứu hồ sơ học sinh</h3><form class="toolbar" id="searchForm"><label>Họ tên hoặc mã<input id="searchText" type="search" value="${escapeHTML(prev.q||'')}" placeholder="Nhập tên hoặc mã HS"></label><label>Lớp ${classSelect('searchClass',prev.class_id||'')}</label><label>Khối <select id="searchGrade"><option value="">Tất cả khối</option>${[10,11,12].map(g=>`<option value="${g}" ${String(prev.grade)===String(g)?'selected':''}>Khối ${g}</option>`).join('')}</select></label><button type="submit" class="primary action">Tìm kiếm</button></form><div id="searchResults">${empty('Nhập từ khóa hoặc chọn lớp để tra cứu.')}</div></section>`;
 async function query(offset=0){const params={q:$('searchText').value.trim(),class_id:$('searchClass').value,grade:$('searchGrade').value,limit:50,offset};s.filters.search=params;const data=await api('/students?'+qs(params));if(!current(v))return;
 $('searchResults').innerHTML=`<p class="hint">${fmtInt(data.total)} học sinh phù hợp</p>${data.items.length?`<div class="table-wrap"><table><thead><tr><th>Mã HS</th><th>Họ tên</th><th>Lớp</th><th>Chi tiết</th></tr></thead><tbody>${data.items.map(x=>`<tr><td>${escapeHTML(x.code)}</td><td>${escapeHTML(x.full_name)}</td><td>${escapeHTML(x.class_name)}</td><td><button class="pill-button" data-student="${escapeHTML(x.code)}">Xem hồ sơ</button></td></tr>`).join('')}</tbody></table></div>`:empty('Không có học sinh phù hợp.')}${data.total>offset+50?`<button id="searchNext" class="secondary">Trang tiếp theo →</button>`:''}${offset>0?`<button id="searchPrev" class="secondary">← Trang trước</button>`:''}`;
 wireStudentLinks($('searchResults'));
 if($('searchNext'))$('searchNext').onclick=()=>query(offset+50).catch(e=>toast(e.message,true));
 if($('searchPrev'))$('searchPrev').onclick=()=>query(Math.max(0,offset-50)).catch(e=>toast(e.message,true));
 }
 $('searchForm').onsubmit=e=>{e.preventDefault();query().catch(err=>toast(err.message,true))};
 await query();
}
async function renderWarnings(v){const prev=s.filters.warnings||{};
 $('pageContent').innerHTML=`<section class="panel"><h3>Danh sách cảnh báo học sinh</h3><form class="toolbar" id="warningForm"><label>Lớp ${classSelect('warnClass',prev.class_id||'')}</label><label>Mức cảnh báo <select id="warnLevel"><option value="">Tất cả</option>${['Tốt','Nhắc nhở','Cần quan tâm','Cảnh báo','Cảnh báo cao'].map(x=>`<option value="${x}" ${prev.level===x?'selected':''}>${x}</option>`).join('')}</select></label><label><span>Chỉ hiện học sinh có cảnh báo</span><select id="warnFlag"><option value="true" ${prev.only_flagged!=='false'?'selected':''}>Có</option><option value="false" ${prev.only_flagged==='false'?'selected':''}>Không</option></select></label><button class="primary action">Lọc</button></form><div id="warningResults"></div></section>`;
 async function load(offset=0){const args={class_id:$('warnClass').value,level:$('warnLevel').value,only_flagged:$('warnFlag').value,limit:80,offset};s.filters.warnings=args;const d=await api('/warnings?'+qs(args));if(!current(v))return;
 $('warningResults').innerHTML=`<p class="hint">${fmtInt(d.total)} kết quả</p>${d.items.length?`<div class="table-wrap"><table><thead><tr><th>Học sinh</th><th>Lớp</th><th>Lượt</th><th>Mức</th><th>Đề nghị GVCN</th></tr></thead><tbody>${d.items.map(x=>`<tr><td><button class="pill-button" data-student="${escapeHTML(x.code)}">${escapeHTML(x.full_name)}</button></td><td>${escapeHTML(x.class_name)}</td><td>${fmtInt(x.total)}</td><td>${warningTag(x.warning)}</td><td>${escapeHTML(x.recommendation)}</td></tr>`).join('')}</tbody></table></div>`:empty('Chưa có học sinh phù hợp.')}${d.total>offset+80?'<button class="secondary" id="warningsNext">Xem tiếp →</button>':''}${offset>0?'<button class="secondary" id="warningsPrev">← Trước</button>':''}`;
 wireStudentLinks($('warningResults'));if($('warningsNext'))$('warningsNext').onclick=()=>load(offset+80).catch(e=>toast(e.message,true));if($('warningsPrev'))$('warningsPrev').onclick=()=>load(Math.max(offset-80,0)).catch(e=>toast(e.message,true));}
 $('warningForm').onsubmit=e=>{e.preventDefault();load().catch(err=>toast(err.message,true))};await load();}
async function renderJournal(v){const p=s.filters.journal||{};
 $('pageContent').innerHTML=`<section class="panel"><div class="section-head"><h3>Nhật ký vi phạm</h3><button id="journalReset" class="secondary">Xóa lọc</button></div><form class="toolbar" id="journalForm"><label>Lớp ${classSelect('journalClass',p.class_id||'')}</label><label>Loại ${typeSelect('journalType',p.type_id||'')}</label><label>Từ ngày<input id="journalStart" type="date" value="${escapeHTML(p.start||'')}"></label><label>Đến ngày<input id="journalEnd" type="date" value="${escapeHTML(p.end||'')}"></label><button class="primary action">Lọc</button></form><div id="journalResults"></div></section>`;
 async function load(offset=0){const args={class_id:$('journalClass').value,type_id:$('journalType').value,start:$('journalStart').value,end:$('journalEnd').value,limit:50,offset};s.filters.journal=args;const d=await api('/violations?'+qs(args));if(!current(v))return;
 $('journalResults').innerHTML=`<p class="hint">${fmtInt(d.total)} bản ghi</p>${d.items.length?`<div class="list-cards">${d.items.map(x=>`<div class="list-card"><div class="item-title">${escapeHTML(x.violation_type)} · <button class="pill-button" data-student="${escapeHTML(x.student_code)}">${escapeHTML(x.student_name)}</button></div><div class="sub">${escapeHTML(x.class_name)} · Ngày xảy ra: ${escapeHTML(x.happened_on)} · Ghi bởi ${escapeHTML(x.recorder)}</div>${x.note?`<div class="sub">Ghi chú: ${escapeHTML(x.note)}</div>`:''}<div class="row edit-actions">${x.photo_count?`<button class="pill-button" data-view-photo="${x.id}">Xem ${x.photo_count} ảnh</button>`:''}${canEdit(x)&&x.photo_count<3?`<button class="pill-button" data-add-photo="${x.id}">+ Ảnh</button>`:''}</div>${canEdit(x)?`<div class="row edit-actions"><button class="pill-button" data-edit="${x.id}">Sửa</button><button class="pill-button danger" data-void="${x.id}">Hủy bản ghi</button></div>`:''}</div>`).join('')}</div>`:empty('Chưa có vi phạm trong khoảng lọc.')}${d.total>offset+50?'<button class="secondary" id="journalNext">Xem tiếp →</button>':''}${offset>0?'<button class="secondary" id="journalPrev">← Trước</button>':''}`;
 wireStudentLinks($('journalResults'));for(const x of d.items){const edit=$('journalResults').querySelector(`[data-edit="${x.id}"]`);if(edit)edit.onclick=()=>editViolation(x);const voidButton=$('journalResults').querySelector(`[data-void="${x.id}"]`);if(voidButton)voidButton.onclick=()=>voidViolation(x);
 const imageButton=$('journalResults').querySelector(`[data-view-photo="${x.id}"]`);if(imageButton)imageButton.onclick=()=>viewEvidence(x);
 const addButton=$('journalResults').querySelector(`[data-add-photo="${x.id}"]`);if(addButton)addButton.onclick=()=>addEvidenceLater(x)};
 if($('journalNext'))$('journalNext').onclick=()=>load(offset+50).catch(e=>toast(e.message,true));if($('journalPrev'))$('journalPrev').onclick=()=>load(Math.max(0,offset-50)).catch(e=>toast(e.message,true));}
 $('journalForm').onsubmit=e=>{e.preventDefault();load().catch(err=>toast(err.message,true))};$('journalReset').onclick=()=>{s.filters.journal={};navigate('journal')};
 await load();}
function canEdit(v){return s.user?.role==='admin'||s.user?.role==='recorder'&&s.user?.id===v.recorded_by}
async function voidViolation(v){const reason=prompt(`Nhập lý do hủy bản ghi #${v.id} (ít nhất 3 ký tự):`);if(reason===null)return;if(reason.trim().length<3){toast('Lý do phải có ít nhất 3 ký tự.',true);return}if(!confirm('Xác nhận hủy bản ghi? Dữ liệu vẫn được giữ trong nhật ký kiểm toán.'))return;try{await api(`/violations/${v.id}/void`,{method:'POST',body:{reason:reason.trim()}});toast('Đã hủy bản ghi.');navigate('journal')}catch(e){toast(e.message,true)}}
function editViolation(v){$('dialogContent').innerHTML=`<h2>Sửa vi phạm #${v.id}</h2><p class="hint">${escapeHTML(v.student_name)} · ${escapeHTML(v.class_name)}</p><form id="editViolationForm" class="stack"><label>Loại vi phạm<select id="editType">${safeOptions(s.types,'id','name',v.violation_type_id)}</select></label><label>Ngày xảy ra<input id="editDate" type="date" value="${escapeHTML(v.happened_on)}" required></label><label>Ghi chú<textarea id="editNote" maxlength="2000">${escapeHTML(v.note||'')}</textarea></label><button class="primary">Lưu thay đổi</button></form>`;$('detailDialog').showModal();$('editViolationForm').onsubmit=async e=>{e.preventDefault();try{await api(`/violations/${v.id}`,{method:'PATCH',body:{violation_type_id:Number($('editType').value),happened_on:$('editDate').value,note:$('editNote').value}});$('detailDialog').close();toast('Đã cập nhật và ghi nhận lịch sử sửa.');navigate('journal')}catch(err){toast(err.message,true)}}}
async function renderReports(v){const now=today();const monday=new Date(now+'T12:00:00');const day=monday.getDay();monday.setDate(monday.getDate()-((day+6)%7));const begin=`${monday.getFullYear()}-${String(monday.getMonth()+1).padStart(2,'0')}-${String(monday.getDate()).padStart(2,'0')}`;const saturday=new Date(monday);saturday.setDate(saturday.getDate()+5);const end=`${saturday.getFullYear()}-${String(saturday.getMonth()+1).padStart(2,'0')}-${String(saturday.getDate()).padStart(2,'0')}`;
 const p=s.filters.report||{start:begin,end};$('pageContent').innerHTML=`<section class="panel"><h3>Báo cáo theo thời gian</h3><p class="hint">Mặc định Thứ Hai–Thứ Bảy; có thể tùy chỉnh khoảng ngày. Báo cáo được tính từ nhật ký thực tế của máy chủ.</p><form id="reportForm" class="toolbar"><label>Từ ngày<input id="reportStart" type="date" value="${escapeHTML(p.start)}" required></label><label>Đến ngày<input id="reportEnd" type="date" value="${escapeHTML(p.end)}" required></label><button class="primary action">Xem báo cáo</button></form><div class="row export-actions"><button class="secondary" id="downloadPdf">↓ Xuất PDF</button><button class="secondary" id="downloadXlsx">↓ Xuất Excel</button></div><div id="reportResults"></div></section>`;
 async function load(){const a=$('reportStart').value,b=$('reportEnd').value;if(a>b)throw new Error('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc');s.filters.report={start:a,end:b};const d=await api('/reports/weekly?'+qs(s.filters.report));if(!current(v))return;
 const rows=d.classes||d.rows||d.by_class||[];$('reportResults').innerHTML=`<div class="notice">Trường THPT Trần Hưng Đạo – Thanh Xuân · ${escapeHTML(d.school_year||d.year||'')} · ${escapeHTML(a)} đến ${escapeHTML(b)}</div><div class="cards report-cards"><div class="stat-card"><div class="kpi-label">Tổng lượt vi phạm</div><div class="kpi-value">${fmtInt(d.total??d.grand_total??rows.reduce((z,x)=>z+(x.total||0),0))}</div></div><div class="stat-card"><div class="kpi-label">Số lớp trong báo cáo</div><div class="kpi-value">${fmtInt(rows.length)}</div></div></div>${rows.length?`<div class="table-wrap"><table><thead><tr><th>Lớp</th><th>Tổng lượt</th>${s.types.map(x=>`<th>${escapeHTML(x.name)}</th>`).join('')}</tr></thead><tbody>${rows.map(x=>`<tr><td>${escapeHTML(x.class_name)}</td><td><b>${fmtInt(x.total)}</b></td>${s.types.map(t=>`<td>${fmtInt((x.by_type||{})[t.name]||0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:empty()}`;}
 $('reportForm').onsubmit=e=>{e.preventDefault();load().catch(err=>toast(err.message,true))};
 async function download(format){if($('reportStart').value>$('reportEnd').value){toast('Khoảng ngày không hợp lệ.',true);return}
 const params=qs({start:$('reportStart').value,end:$('reportEnd').value});try{const response=await fetch(`/reports/weekly.${format}?${params}`,{headers:{'Authorization':'Bearer '+s.token},cache:'no-store'});if(!response.ok)throw new Error('Không tải được báo cáo ('+response.status+')');const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`thd-bao-cao-${$('reportStart').value}-${$('reportEnd').value}.${format}`;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),15000);toast('Đã bắt đầu tải báo cáo '+format.toUpperCase())}catch(e){toast(e.message,true)}}
 $('downloadPdf').onclick=()=>download('pdf');$('downloadXlsx').onclick=()=>download('xlsx');await load();}
async function renderAdmin(v){if(s.user?.role!=='admin'){$('pageContent').innerHTML=empty('Không có quyền quản trị.');return}const [users,rules,years]=await Promise.all([api('/admin/users'),api('/admin/warning-rules'),api('/school-years')]);if(!current(v))return;
 $('pageContent').innerHTML=`<div class="two-col"><section class="panel"><h3>Tài khoản và phân quyền</h3><p class="hint">Tài khoản giới hạn theo lớp được phân công. Mật khẩu cần tối thiểu 12 ký tự.</p><form id="newUserForm" class="stack"><label>Tên đăng nhập<input id="newUsername" required pattern="[A-Za-z0-9._-]+" minlength="3"></label><label>Họ tên người dùng<input id="newDisplayName" required minlength="2"></label><label>Mật khẩu khởi tạo<input id="newPassword" type="password" required minlength="12"></label><label>Vai trò<select id="newRole"><option value="recorder">Giáo viên trực / nhập liệu</option><option value="homeroom">Giáo viên chủ nhiệm</option><option value="leadership">Ban giám hiệu / Ban Đức dục</option><option value="admin">Quản trị viên</option></select></label><label>Lớp được cấp quyền (giữ Ctrl để chọn nhiều; vai trò toàn trường được cấp theo quy định)<select id="newClasses" size="5" multiple>${safeOptions(s.classes,'id','name')}</select></label><button class="primary">Tạo tài khoản</button></form></section><section class="panel"><h3>Tình trạng cấu hình</h3><p class="hint">Năm học: ${years.map(y=>`${escapeHTML(y.name)} ${y.active?'(đang hoạt động)':''}`).join(', ')}</p><p class="hint">Ngưỡng hiện tại:</p>${rules.map(r=>`<div class="list-card">${escapeHTML(r.min_count)}–${r.max_count??'∞'} lượt: ${warningTag(r.label)} <span class="hint">(bản ${r.version})</span></div>`).join('')}<p class="notice">Cấu hình cảnh báo nâng cao và import Excel thực hiện bởi quản trị trên máy chủ, có kiểm toán.</p></section></div><section class="panel"><h3>Danh sách tài khoản</h3><div class="table-wrap"><table><thead><tr><th>Tài khoản</th><th>Người dùng</th><th>Vai trò</th><th>Trạng thái</th></tr></thead><tbody>${users.map(u=>`<tr><td>${escapeHTML(u.username)}</td><td>${escapeHTML(u.display_name)}</td><td>${escapeHTML(u.role)}</td><td>${u.is_active?'Hoạt động':'Đã khóa'}</td></tr>`).join('')}</tbody></table></div></section>`;
 $('newUserForm').onsubmit=async e=>{e.preventDefault();const password=$('newPassword').value;const user={username:$('newUsername').value.trim(),display_name:$('newDisplayName').value.trim(),password,role:$('newRole').value,class_ids:Array.from($('newClasses').selectedOptions).map(o=>Number(o.value))};try{await api('/admin/users',{method:'POST',body:user});toast('Đã tạo tài khoản thành công.');navigate('admin')}catch(err){toast(err.message,true)}};
}
$('loginForm').addEventListener('submit',logIn);$('logoutButton').onclick=logout;$('refreshBtn').onclick=()=>navigate(s.page);$('closeDialog').onclick=()=>$('detailDialog').close();$('detailDialog').addEventListener('click',e=>{if(e.target===$('detailDialog'))$('detailDialog').close()});
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();s.installEvent=e;$('installBtn').classList.remove('hidden')});$('installBtn').onclick=async()=>{if(!s.installEvent)return;s.installEvent.prompt();await s.installEvent.userChoice;s.installEvent=null;$('installBtn').classList.add('hidden')};
if('serviceWorker' in navigator&&window.isSecureContext){navigator.serviceWorker.register('/app/sw.js',{scope:'/app/'}).catch(()=>{})}
// Periodic synchronization is read-only; never auto-submit a form, and never rewrite an in-progress draft.
setInterval(()=>{if(s.token&&!document.hidden&&['home','warnings','journal','reports'].includes(s.page)&&!$('detailDialog').open)navigate(s.page)},30000);
