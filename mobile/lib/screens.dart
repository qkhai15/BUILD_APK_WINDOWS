import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'api.dart';
import 'branding.dart';

const gap = SizedBox(height: 12);
final dateFormatter = DateFormat('dd/MM/yyyy');
String dateUi(String? raw) { try { return dateFormatter.format(DateTime.parse(raw!)); } catch (_) { return raw ?? '—'; } }
String errorText(Object error) => error is ApiException ? error.message : 'Lỗi không xác định: $error';
void showError(BuildContext context,Object error) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(errorText(error)),backgroundColor:Colors.red.shade700));
void showSuccess(BuildContext context,String message) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(message)));

Widget loadState(AsyncSnapshot<dynamic> snap,{required Widget Function(dynamic) done}) {
  if(snap.connectionState!=ConnectionState.done) return const Center(child:CircularProgressIndicator());
  if(snap.hasError) return Center(child:Padding(padding:const EdgeInsets.all(24),child:Text(errorText(snap.error!),textAlign:TextAlign.center)));
  return done(snap.data);
}

class HomeScreen extends StatefulWidget {
  final ThdApi api;final int revision;
  const HomeScreen({super.key,required this.api,required this.revision});
  @override State<HomeScreen> createState()=> _HomeScreenState();
}
class _HomeScreenState extends State<HomeScreen> {
  late Future<dynamic> future;String? start,end;
  void reload(){future=widget.api.get('/dashboard',{'start':start,'end':end});}
  @override void initState(){super.initState();reload();}
  @override void didUpdateWidget(covariant HomeScreen old){super.didUpdateWidget(old);if(old.revision!=widget.revision)reload();}
  Future<void> changeRange() async {
    final now=DateTime.now();
    final chosen=await showDateRangePicker(context:context,firstDate:DateTime(2020),lastDate:DateTime(2040),
      initialDateRange:DateTimeRange(start:DateTime.tryParse(start??'')??now,end:DateTime.tryParse(end??'')??now));
    if(chosen!=null)setState((){start=DateFormat('yyyy-MM-dd').format(chosen.start);end=DateFormat('yyyy-MM-dd').format(chosen.end);reload();});
  }
  @override Widget build(BuildContext context)=> FutureBuilder(future:future,builder:(context,s)=>loadState(s,done:(value){
    final data=value as Map<String,dynamic>;final classes=(data['by_class'] as List).cast<Map<String,dynamic>>();
    final top=[...classes]..sort((a,b)=>(b['total'] as int).compareTo(a['total'] as int));
    final shown=top.take(12).toList();
    final counts=(data['by_type'] as Map).values;
    final maxCount=counts.fold<int>(1,(current,value)=>(value as int)>current?value:current);
    return RefreshIndicator(onRefresh:()async{setState(reload);await future;},child:ListView(padding:const EdgeInsets.all(16),children:[
      const Card(child: Padding(padding: EdgeInsets.symmetric(vertical: 14, horizontal: 10), child: SchoolBranding(logoSize: 50, withSchoolName: true))),
      gap,
      Text('Toàn trường / Phạm vi được cấp quyền',style:Theme.of(context).textTheme.titleMedium),
      gap,
      OutlinedButton.icon(onPressed:changeRange,icon:const Icon(Icons.date_range),
        label:Text(start==null?'Thống kê tất cả ngày':'Từ ${dateUi(start)} đến ${dateUi(end)}')),
      Wrap(spacing:10,runSpacing:10,children:[
        metric(context,'Vi phạm hôm nay',data['today_total'],Icons.today,today:true,day:data['today'] as String),
        metric(context,'Đi học muộn',data['today_late'],Icons.access_time,type:'Đi học muộn',today:true,day:data['today'] as String),
        metric(context,'Nghỉ không phép',data['today_absent'],Icons.event_busy,type:'Nghỉ học không phép',today:true,day:data['today'] as String),
        metric(context,'Tổng đã ghi nhận',data['all_total'],Icons.fact_check_outlined),
      ]),
      const SizedBox(height:20),
      Row(children:[Text('Thống kê theo lớp',style:Theme.of(context).textTheme.titleLarge),const Spacer(),Text('${classes.length} lớp')]),
      gap,
      if(shown.isEmpty)const Text('Chưa có lớp trong phạm vi được cấp quyền.'),
      for(final c in shown)Card(child:ListTile(
        title:Text(c['class_name'] as String),
        subtitle:Text('Khối ${c['grade']}  •  ${c['warning']}'),
        trailing:Text('${c['total']} lượt',style:const TextStyle(fontWeight:FontWeight.bold)),
        onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>ClassDetailScreen(api:widget.api,classId:c['class_id'] as int,name:c['class_name'] as String))),
      )),
      if(top.length>12)const Padding(padding:EdgeInsets.all(8),child:Text('Hiển thị 12 lớp nhiều lượt nhất. Vào mục Tra cứu để xem lớp khác.')),
      gap, Text('Thống kê theo loại',style:Theme.of(context).textTheme.titleLarge),gap,
      for(final entry in (data['by_type'] as Map).entries)ListTile(
        dense:true,title:Text('${entry.key}'),
        subtitle:LinearProgressIndicator(minHeight:6,value: (entry.value as int)/maxCount),
        trailing:Text('${entry.value} lượt'),
        onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>JournalScreen(api:widget.api,initialTypeName:'${entry.key}',initialStart:start,initialEnd:end))),
      ),
    ]));
  }));
  Widget metric(BuildContext ctx,String label,dynamic value,IconData icon,{bool today=false,String? type,String? day})=>SizedBox(width:(MediaQuery.of(ctx).size.width-46)/2,
    child:Card(child:InkWell(borderRadius:BorderRadius.circular(16),onTap:()=>Navigator.push(ctx,MaterialPageRoute(builder:(_)=>JournalScreen(
      api:widget.api,initialTypeName:type,initialStart:today?day:null,initialEnd:today?day:null))),
      child:Padding(padding:const EdgeInsets.all(14),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Icon(icon,color:Theme.of(ctx).colorScheme.primary),gap,Text('$value',style:Theme.of(ctx).textTheme.headlineMedium?.copyWith(fontWeight:FontWeight.bold)),Text(label,style:const TextStyle(fontSize:12))
    ])))));
}

class RecordScreen extends StatefulWidget {
  final ThdApi api;final VoidCallback onSaved;
  const RecordScreen({super.key,required this.api,required this.onSaved});
  @override State<RecordScreen> createState()=>_RecordScreenState();
}
class _RecordScreenState extends State<RecordScreen> {
  late Future<void> initial;
  List<dynamic> classes=[],types=[],students=[];
  int? classId,typeId;String? studentCode;String? currentDate;
  final note=TextEditingController();bool saving=false;
  final List<XFile> chosenPhotos=[]; int? pendingViolationId; int uploadedPhotos=0; bool submissionUncertain=false;
  String requestKey=const Uuid().v4();
  @override void initState(){super.initState();initial=load();}
  @override void dispose(){note.dispose();super.dispose();}
  Future<void> load() async {
    final result=await Future.wait([widget.api.get('/classes'),widget.api.get('/violation-types'),widget.api.get('/dashboard')]);
    classes=result[0] as List;types=result[1] as List;currentDate=(result[2] as Map)['today'] as String;
  }
  Future<void> changeClass(int? id) async {
    setState((){classId=id;studentCode=null;students=[];requestKey=const Uuid().v4();});
    if(id==null)return;
    try {
      final r=await widget.api.get('/students',{'class_id':'$id','limit':'150'});
      if(mounted && classId==id)setState(()=>students=(r as Map)['items'] as List);
    }catch(e){if(mounted)showError(context,e);}
  }
  Future<void> save() async {
    if(!widget.api.canRecord){showError(context,const ApiException(403,'Tài khoản chỉ có quyền xem'));return;}
    if(studentCode==null || typeId==null){showError(context,const ApiException(422,'Hãy chọn học sinh và loại vi phạm.'));return;}
    if(saving)return;
    setState(()=>saving=true);
    try {
      if(pendingViolationId == null){
        submissionUncertain=true;
        final result=await widget.api.post('/violations',{'student_code':studentCode,'violation_type_id':typeId,
          'happened_on':currentDate,'note':note.text.trim()},key:requestKey) as Map;
        pendingViolationId=result['id'] as int;
      }
      // If one picture fails, do not resend another violation or already uploaded photos.
      while(uploadedPhotos<chosenPhotos.length){
        final image = chosenPhotos[uploadedPhotos];
        final bytes = await image.readAsBytes();
        await widget.api.uploadPhoto(pendingViolationId!,bytes);
        uploadedPhotos++;
      }
      if(!mounted)return;
      showSuccess(context,'Đã lưu vi phạm${chosenPhotos.isEmpty ? '' : ' và ${chosenPhotos.length} ảnh'} trên máy chủ');
      setState(() { studentCode=null;typeId=null;note.clear();requestKey=const Uuid().v4();
        chosenPhotos.clear();pendingViolationId=null;uploadedPhotos=0;submissionUncertain=false; });
      widget.onSaved();
    } catch(e){
      if(pendingViolationId==null && e is ApiException && e.status>=400)submissionUncertain=false;
      if(mounted)showError(context,e);
    }
    finally{if(mounted)setState(()=>saving=false);} 
  }
  Future<void> pickPhoto(ImageSource source) async {
    if(pendingViolationId!=null||submissionUncertain){showError(context,const ApiException(409,'Bản ghi đã lưu. Hãy gửi hết ảnh còn lại trước khi tạo bản ghi mới.'));return;}
    if(chosenPhotos.length>=3){showError(context,const ApiException(422,'Mỗi vi phạm tối đa 3 ảnh.'));return;}
    try {
      final picked=await ImagePicker().pickImage(source:source,maxWidth:1600,maxHeight:1600,
        imageQuality:75,requestFullMetadata:false);
      if(picked==null)return;
      final size=await picked.length();
      if(size > 8*1024*1024){if(mounted)showError(context,const ApiException(413,'Ảnh lớn hơn 8 MB, hãy chọn ảnh nhỏ hơn.'));return;}
      if(mounted)setState(()=>chosenPhotos.add(picked));
    }catch(e){if(mounted)showError(context,e);}
  }
  @override Widget build(BuildContext context)=>FutureBuilder<void>(future:initial,builder:(context,s)=>loadState(s,done:(_){
    if(!widget.api.canRecord)return const Center(child:Text('Tài khoản này không được phép nhập vi phạm.'));
    return ListView(padding:const EdgeInsets.all(18),children:[
      Text('Ghi nhận nhanh',style:Theme.of(context).textTheme.headlineSmall),
      const Text('Dữ liệu được lưu trực tiếp trên máy chủ; không hỗ trợ nhập offline.'),
      const SizedBox(height:22),
      DropdownButtonFormField<int>(value:classId,decoration:const InputDecoration(labelText:'1. Chọn lớp'),
        items:classes.map((c)=>DropdownMenuItem<int>(value:c['id'] as int,child:Text(c['name'] as String))).toList(),onChanged:pendingViolationId==null&&!submissionUncertain?changeClass:null),
      gap,
      DropdownButtonFormField<String>(value:studentCode,decoration:const InputDecoration(labelText:'2. Chọn học sinh'),isExpanded:true,
        items:students.map((s)=>DropdownMenuItem<String>(value:s['code'] as String,child:Text('${s['full_name']} (${s['code']})',overflow:TextOverflow.ellipsis))).toList(),
        onChanged:classId==null||pendingViolationId!=null||submissionUncertain?null:(v)=>setState((){studentCode=v;requestKey=const Uuid().v4();})),
      if(studentCode!=null)Padding(padding:const EdgeInsets.symmetric(vertical:10),child:Text('Mã HS: $studentCode  •  Lớp: ${classes.where((e)=>e['id']==classId).first['name']}')),
      gap,
      DropdownButtonFormField<int>(value:typeId,isExpanded:true,decoration:const InputDecoration(labelText:'3. Loại vi phạm'),
        items:types.map((t)=>DropdownMenuItem<int>(value:t['id'] as int,child:Text(t['name'] as String))).toList(),
        onChanged:pendingViolationId==null&&!submissionUncertain?(v)=>setState((){typeId=v;requestKey=const Uuid().v4();}):null),
      gap,
      ListTile(contentPadding:EdgeInsets.zero,title:const Text('Ngày vi phạm'),subtitle:Text(dateUi(currentDate)),
        trailing:const Icon(Icons.calendar_month),onTap:pendingViolationId!=null||submissionUncertain?null:()async{
          final today=DateTime.tryParse(currentDate??'')??DateTime.now();
          final picked=await showDatePicker(context:context,initialDate:today,firstDate:DateTime(2020),lastDate:DateTime(2040));
          if(picked!=null)setState((){currentDate=DateFormat('yyyy-MM-dd').format(picked);requestKey=const Uuid().v4();});
        }),
      TextField(controller:note,maxLines:3,maxLength:2000,readOnly:pendingViolationId!=null||submissionUncertain,onChanged:(_){ // do not change key while retry after uncertain network result
        },decoration:const InputDecoration(labelText:'Ghi chú (không bắt buộc)')),
      gap,
      const Text('Ảnh minh chứng (tối đa 3 ảnh, không bắt buộc)',style:TextStyle(fontWeight:FontWeight.w600)),
      Row(children:[
        Expanded(child:OutlinedButton.icon(onPressed:saving||pendingViolationId!=null||submissionUncertain?null:()=>pickPhoto(ImageSource.camera),
          icon:const Icon(Icons.camera_alt_outlined),label:const Text('Chụp ảnh'))),
        const SizedBox(width:8),
        Expanded(child:OutlinedButton.icon(onPressed:saving||pendingViolationId!=null||submissionUncertain?null:()=>pickPhoto(ImageSource.gallery),
          icon:const Icon(Icons.photo_library_outlined),label:const Text('Chọn ảnh'))),
      ]),
      if(chosenPhotos.isNotEmpty)Wrap(spacing:8,runSpacing:8,children:[
        for(var i=0;i<chosenPhotos.length;i++) Stack(children:[
          ClipRRect(borderRadius:BorderRadius.circular(8),child:Image.file(File(chosenPhotos[i].path),width:100,height:100,fit:BoxFit.cover)),
          if(!saving && pendingViolationId==null && !submissionUncertain)Positioned(right:0,top:0,child:IconButton(
            style:IconButton.styleFrom(backgroundColor:Colors.white),icon:const Icon(Icons.close,size:17),
            onPressed:()=>setState(()=>chosenPhotos.removeAt(i)))),
        ])
      ]),
      if(pendingViolationId!=null)Padding(padding:const EdgeInsets.symmetric(vertical:8),
        child:Text('Đã tạo vi phạm #$pendingViolationId. Đã gửi $uploadedPhotos/${chosenPhotos.length} ảnh. Chọn tiếp tục để hoàn thành.',
          style:const TextStyle(color:Colors.deepOrange))),
      gap,
      FilledButton.icon(onPressed:saving?null:save,icon:saving?const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2)):const Icon(Icons.save),
        label:Text(pendingViolationId!=null?'Tiếp tục gửi ảnh':'Lưu vi phạm${chosenPhotos.isNotEmpty?' kèm ảnh':''}'))),
      const SizedBox(height:14),
      const Text('Khi gặp lỗi mạng sau khi nhấn Lưu, thử lại cùng màn hình; ứng dụng giữ khóa chống ghi trùng cho lần gửi này.',style:TextStyle(fontSize:12,color:Colors.black54)),
    ]);
  }));
}

/// Evidence images are fetched with the same authenticated request and NEVER public URLs.
Future<void> showViolationPhotos(BuildContext context, ThdApi api, Map violation) async {
  final photoList = (violation['photos'] as List?) ?? [];
  if(photoList.isEmpty){showError(context,const ApiException(404,'Không có ảnh minh chứng.'));return;}
  await showDialog<void>(context:context,builder:(dialogContext)=>AlertDialog(
    title:Text('Ảnh minh chứng #${violation['id']}'),
    content:SizedBox(width:360,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,
      children:[for(final photo in photoList)Padding(padding:const EdgeInsets.only(bottom:12),
        child:FutureBuilder(future:api.photoBytes(violation['id'] as int,photo['id'] as int),
          builder:(context,s)=>loadState(s,done:(bytes)=>Image.memory(bytes,width:340,fit:BoxFit.contain))))]))),
    actions:[TextButton(onPressed:()=>Navigator.pop(dialogContext),child:const Text('Đóng'))],
  ));
}

Future<bool> addPhotoToExisting(BuildContext context, ThdApi api, Map violation) async {
  if((violation['photo_count'] as int? ?? 0)>=3){
    showError(context,const ApiException(422,'Bản ghi đã đủ 3 ảnh.'));return false;
  }
  final source=await showModalBottomSheet<ImageSource>(context:context,builder:(sheetContext)=>SafeArea(
    child:Wrap(children:[
      ListTile(leading:const Icon(Icons.camera_alt_outlined),title:const Text('Chụp ảnh'),
        onTap:()=>Navigator.pop(sheetContext,ImageSource.camera)),
      ListTile(leading:const Icon(Icons.photo_library_outlined),title:const Text('Chọn ảnh trong máy'),
        onTap:()=>Navigator.pop(sheetContext,ImageSource.gallery)),
    ])));
  if(source==null)return false;
  try{
    final picked=await ImagePicker().pickImage(source:source,maxWidth:1600,maxHeight:1600,
      imageQuality:75,requestFullMetadata:false);
    if(picked==null)return false;
    await api.uploadPhoto(violation['id'] as int,await picked.readAsBytes());
    if(context.mounted)showSuccess(context,'Đã bổ sung ảnh vào bản ghi #${violation['id']}');
    return true;
  }catch(e){if(context.mounted)showError(context,e);return false;}
}

class SearchScreen extends StatefulWidget {
  final ThdApi api;final int revision;
  const SearchScreen({super.key,required this.api,required this.revision});
  @override State<SearchScreen> createState()=>_SearchScreenState();
}
class _SearchScreenState extends State<SearchScreen> {
  final search=TextEditingController();List<dynamic> items=[],classes=[];
  int? classId,grade;int offset=0;int total=0;bool loading=true;String? error;
  @override void initState(){super.initState();initialize();}
  @override void didUpdateWidget(covariant SearchScreen old){super.didUpdateWidget(old);if(old.revision!=widget.revision)fetch(reset:true);}
  @override void dispose(){search.dispose();super.dispose();}
  Future<void> initialize()async{
    try{classes=await widget.api.get('/classes') as List;await fetch(reset:true);}catch(e){if(mounted)setState((){error=errorText(e);loading=false;});}
  }
  Future<void> fetch({required bool reset})async{
    if(reset){offset=0;items=[];}setState((){loading=true;error=null;});
    try{
      final d=await widget.api.get('/students',{'q':search.text.trim(),'class_id':classId?.toString(),'grade':grade?.toString(),'offset':'$offset','limit':'50'}) as Map;
      if(!mounted)return;
      setState((){items.addAll(d['items'] as List);total=d['total'] as int;offset=items.length;loading=false;});
    }catch(e){if(mounted)setState((){error=errorText(e);loading=false;});}
  }
  @override Widget build(BuildContext context)=>ListView(padding:const EdgeInsets.all(14),children:[
    TextField(controller:search,onSubmitted:(_)=>fetch(reset:true),decoration:InputDecoration(labelText:'Mã, họ tên hoặc lớp',prefixIcon:const Icon(Icons.search),suffixIcon:IconButton(onPressed:()=>fetch(reset:true),icon:const Icon(Icons.arrow_forward)))),
    gap,
    Row(children:[Expanded(child:DropdownButtonFormField<int>(value:grade,decoration:const InputDecoration(labelText:'Khối'),items:const [
      DropdownMenuItem(value:null,child:Text('Tất cả')),DropdownMenuItem(value:10,child:Text('10')),DropdownMenuItem(value:11,child:Text('11')),DropdownMenuItem(value:12,child:Text('12'))],
      onChanged:(v){setState((){grade=v;classId=null;});fetch(reset:true);})),
      const SizedBox(width:8),
      Expanded(child:DropdownButtonFormField<int>(value:classId,isExpanded:true,decoration:const InputDecoration(labelText:'Lớp'),
        items:[const DropdownMenuItem<int>(value:null,child:Text('Tất cả')),
          ...classes.where((c)=>grade==null||c['grade']==grade).map((c)=>DropdownMenuItem<int>(value:c['id'] as int,child:Text(c['name'] as String)))],
        onChanged:(v){setState(()=>classId=v);fetch(reset:true);})),
    ]),gap,
    Text('$total học sinh',style:Theme.of(context).textTheme.titleMedium),
    if(error!=null)Text(error!,style:const TextStyle(color:Colors.red)),
    if(items.isEmpty&&!loading)const Padding(padding:EdgeInsets.all(28),child:Center(child:Text('Không có học sinh phù hợp.'))),
    for(final s in items)Card(child:ListTile(title:Text(s['full_name'] as String),subtitle:Text('${s['code']}  •  ${s['class_name']}'),
      trailing:const Icon(Icons.chevron_right),onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StudentDetailScreen(api:widget.api,code:s['code'] as String))))),
    if(loading)const Padding(padding:EdgeInsets.all(18),child:Center(child:CircularProgressIndicator())),
    if(items.length<total&&!loading)TextButton(onPressed:()=>fetch(reset:false),child:const Text('Tải thêm học sinh')),
  ]);
}

class StudentDetailScreen extends StatefulWidget {
  final ThdApi api;final String code;
  const StudentDetailScreen({super.key,required this.api,required this.code});
  @override State<StudentDetailScreen> createState()=>_StudentDetailScreenState();
}
class _StudentDetailScreenState extends State<StudentDetailScreen> {
  late Future<dynamic> future;
  @override void initState(){super.initState();reload();}
  void reload(){future=widget.api.get('/students/${Uri.encodeComponent(widget.code)}');}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Hồ sơ học sinh'),actions:[IconButton(onPressed:()=>setState(reload),icon:const Icon(Icons.refresh))]),
    body:FutureBuilder(future:future,builder:(context,s)=>loadState(s,done:(raw){
      final d=raw as Map;final types=d['by_type'] as Map;
      return ListView(padding:const EdgeInsets.all(16),children:[
        Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
          Text(d['full_name'] as String,style:Theme.of(context).textTheme.headlineSmall),gap,
          Text('Mã: ${d['code']}  •  Lớp: ${d['class_name']}'),
          Text('Ngày sinh: ${dateUi(d['birth_date'] as String)}  •  ${d['gender']}'),
          gap,Text('${d['total']} lượt  •  ${d['warning']}',style:const TextStyle(fontWeight:FontWeight.bold)),
          Text('Đề nghị GVCN: ${d['recommendation']}'),
        ]))),gap,
        Text('Thống kê theo loại',style:Theme.of(context).textTheme.titleMedium),
        for(final t in types.entries)ListTile(dense:true,title:Text(t.key as String),trailing:Text('${t.value}')),
        gap,Text('Lịch sử vi phạm',style:Theme.of(context).textTheme.titleMedium),
        if((d['history'] as List).isEmpty)const Text('Học sinh chưa có vi phạm được ghi nhận.'),
        for(final v in d['history'])Card(child:Column(children:[ListTile(title:Text(v['violation_type'] as String),subtitle:Text('${dateUi(v['happened_on'] as String)}  •  ${v['recorder']}\n${v['note']??''}'),isThreeLine:true),
          if((v['photo_count'] as int? ?? 0)>0)TextButton.icon(
            onPressed:()=>showViolationPhotos(context,widget.api,v as Map),
            icon:const Icon(Icons.photo_outlined),label:Text('Xem ${v['photo_count']} ảnh minh chứng')),
          if(widget.api.canRecord && (v['photo_count'] as int? ?? 0)<3)TextButton.icon(
            onPressed:()async{final done=await addPhotoToExisting(context,widget.api,v as Map);
              if(done && mounted)setState(reload);},
            icon:const Icon(Icons.add_a_photo_outlined),label:const Text('Bổ sung ảnh')),
          if(widget.api.canRecord)Padding(padding:const EdgeInsets.only(right:12,bottom:6),child:Row(mainAxisAlignment:MainAxisAlignment.end,children:[
            TextButton(onPressed:()async{final done=await editViolation(context,widget.api,v);if(done && mounted)setState(reload);},child:const Text('Sửa')),
            TextButton(onPressed:()async{final done=await voidViolation(context,widget.api,v);if(done && mounted)setState(reload);},child:const Text('Hủy')),
          ]))])),
      ]);
    })));
}

Future<bool> editViolation(BuildContext ctx,ThdApi api,dynamic violation) async {
  final note=TextEditingController(text:violation['note']??'');
  final date=TextEditingController(text:violation['happened_on']);
  final types=await api.get('/violation-types') as List;
  int id=violation['violation_type_id'] as int;
  if(!ctx.mounted)return false;
  final ok=await showDialog<bool>(context:ctx,builder:(context)=>StatefulBuilder(builder:(context,refresh)=>AlertDialog(
    title:const Text('Sửa bản ghi'),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
      DropdownButtonFormField<int>(value:id,isExpanded:true,items:types.map((t)=>DropdownMenuItem<int>(value:t['id'] as int,child:Text(t['name'] as String))).toList(),onChanged:(v)=>refresh(()=>id=v??id)),gap,
      TextField(controller:date,decoration:const InputDecoration(labelText:'Ngày YYYY-MM-DD'),readOnly:true,onTap:()async{
        final picked=await showDatePicker(context:context,initialDate:DateTime.parse(date.text),firstDate:DateTime(2020),lastDate:DateTime(2040));
        if(picked!=null)date.text=DateFormat('yyyy-MM-dd').format(picked);
      }),gap,TextField(controller:note,maxLines:3,decoration:const InputDecoration(labelText:'Ghi chú')),
    ])),actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('Đóng')),
      FilledButton(onPressed:()async{
        try{await api.patch('/violations/${violation['id']}',{'violation_type_id':id,'happened_on':date.text,'note':note.text});
          if(context.mounted)Navigator.pop(context,true);
        }catch(e){if(context.mounted)showError(context,e);}
      },child:const Text('Lưu thay đổi'))],
  )));
  note.dispose();date.dispose();return ok??false;
}

Future<bool> voidViolation(BuildContext ctx,ThdApi api,dynamic violation) async {
  final reason=TextEditingController();
  final ok=await showDialog<bool>(context:ctx,builder:(context)=>AlertDialog(title:const Text('Hủy bản ghi (xóa mềm)'),
    content:TextField(controller:reason,maxLines:2,decoration:const InputDecoration(labelText:'Lý do hủy bắt buộc')),
    actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('Đóng')),
      FilledButton(onPressed:()async{
        if(reason.text.trim().length<3){showError(context,const ApiException(422,'Hãy nhập lý do hủy'));return;}
        try{await api.post('/violations/${violation['id']}/void',{'reason':reason.text.trim()});if(context.mounted)Navigator.pop(context,true);}
        catch(e){if(context.mounted)showError(context,e);}
      },child:const Text('Xác nhận hủy'))],));
  reason.dispose();return ok??false;
}

class ClassDetailScreen extends StatefulWidget {
  final ThdApi api;final int classId;final String name;
  const ClassDetailScreen({super.key,required this.api,required this.classId,required this.name});
  @override State<ClassDetailScreen> createState()=>_ClassDetailScreenState();
}
class _ClassDetailScreenState extends State<ClassDetailScreen> {
  late Future<dynamic> future;
  @override void initState(){super.initState();future=widget.api.get('/classes/${widget.classId}/summary');}
  final classQuery=TextEditingController();bool descending=true;
  @override void dispose(){classQuery.dispose();super.dispose();}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:Text('Lớp ${widget.name}')),
    body:FutureBuilder(future:future,builder:(context,s)=>loadState(s,done:(raw){
      final d=raw as Map;final students=(d['students'] as List).where((x)=>
        '${x['full_name']} ${x['code']}'.toLowerCase().contains(classQuery.text.toLowerCase().trim())).toList()
        ..sort((a,b)=>descending?(b['total'] as int).compareTo(a['total'] as int):(a['total'] as int).compareTo(b['total'] as int));
      return ListView(padding:const EdgeInsets.all(16),children:[
        Card(child:Padding(padding:const EdgeInsets.all(16),child:Wrap(spacing:20,runSpacing:14,children:[
          summary('Sĩ số','${d['headcount']}'),summary('HS có vi phạm','${d['students_with_violations']}'),
          summary('Tổng lượt','${d['total']}'),summary('Nghiêm trọng','${d['severe_total']}'),summary('Loại phát sinh','${d['different_types']}'),
        ]))),gap,
        TextField(controller:classQuery,onChanged:(_)=>setState((){}),decoration:const InputDecoration(
          labelText:'Tìm học sinh trong lớp',prefixIcon:Icon(Icons.search))),
        TextButton.icon(onPressed:()=>setState(()=>descending=!descending),
          icon:const Icon(Icons.sort),label:Text(descending?'Sắp xếp tổng lượt: cao đến thấp':'Sắp xếp tổng lượt: thấp đến cao')),gap,
        for(final s in students)Card(child:ListTile(title:Text(s['full_name'] as String),subtitle:Text('${s['code']} • ${s['warning']}'),
          trailing:Text('${s['total']} lượt'),onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StudentDetailScreen(api:widget.api,code:s['code'] as String))))),
      ]);
    })));
  Widget summary(String name,String value)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(name,style:const TextStyle(fontSize:12)),Text(value,style:const TextStyle(fontSize:20,fontWeight:FontWeight.bold))]);
}

class WarningScreen extends StatefulWidget {
  final ThdApi api;final int revision;
  const WarningScreen({super.key,required this.api,required this.revision});
  @override State<WarningScreen> createState()=>_WarningScreenState();
}
class _WarningScreenState extends State<WarningScreen> {
  late Future<dynamic> future;
  String? level;bool flagged=true;int offset=0;
  @override void initState(){super.initState();reload();}
  @override void didUpdateWidget(covariant WarningScreen old){super.didUpdateWidget(old);if(old.revision!=widget.revision)reload();}
  void reload(){future=widget.api.get('/warnings',{'level':level,'only_flagged':'$flagged','offset':'$offset','limit':'80'});}
  @override Widget build(BuildContext context)=>Column(children:[
    Padding(padding:const EdgeInsets.all(12),child:Column(children:[
      DropdownButtonFormField<String>(value:level,isExpanded:true,decoration:const InputDecoration(labelText:'Mức cảnh báo'),items:[
        const DropdownMenuItem(value:null,child:Text('Tất cả mức')),
        for(final x in ['Tốt','Nhắc nhở','Cần quan tâm','Cảnh báo','Cảnh báo cao'])DropdownMenuItem(value:x,child:Text(x))],
        onChanged:(v)=>setState((){level=v;offset=0;reload();})),
      SwitchListTile(title:const Text('Chỉ hiển thị học sinh cần theo dõi'),value:flagged,
        onChanged:(v)=>setState((){flagged=v;offset=0;reload();})),
    ])),
    Expanded(child:FutureBuilder(future:future,builder:(context,s)=>loadState(s,done:(raw){
      final data=raw as Map;final items=data['items'] as List;final total=data['total'] as int;
      return ListView(padding:const EdgeInsets.all(10),children:[
        Text('$total học sinh phù hợp',style:Theme.of(context).textTheme.titleMedium),
        if(items.isEmpty)const Padding(padding:EdgeInsets.all(30),child:Text('Không có học sinh trong nhóm cảnh báo này.')),
        for(final x in items)Card(child:ListTile(title:Text(x['full_name'] as String),
          subtitle:Text('${x['class_name']}  •  ${x['warning']}  •  ${x['recommendation']}'),
          trailing:Text('${x['total']} lượt'),isThreeLine:true,
          onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StudentDetailScreen(api:widget.api,code:x['code'] as String))))),
        if(total>80)Row(mainAxisAlignment:MainAxisAlignment.center,children:[
          IconButton(onPressed:offset>0?()=>setState((){offset=(offset-80).clamp(0,total).toInt();reload();}):null,icon:const Icon(Icons.chevron_left)),
          Text('${offset+1}–${(offset+items.length)} / $total'),
          IconButton(onPressed:offset+80<total?()=>setState((){offset+=80;reload();}):null,icon:const Icon(Icons.chevron_right)),
        ]),
      ]);
    })))
  ]);
}

class JournalScreen extends StatefulWidget {
  final ThdApi api;final String? initialTypeName,initialStart,initialEnd;
  final int? initialClassId;
  const JournalScreen({super.key,required this.api,this.initialTypeName,this.initialStart,this.initialEnd,this.initialClassId});
  @override State<JournalScreen> createState()=>_JournalScreenState();
}
class _JournalScreenState extends State<JournalScreen> {
  final search=TextEditingController();
  List<dynamic> classes=[],types=[];int? classId,typeId;DateTimeRange? range;
  int offset=0;late Future<dynamic> future;
  @override void initState(){super.initState();classId=widget.initialClassId;
    if(widget.initialStart!=null && widget.initialEnd!=null){final a=DateTime.tryParse(widget.initialStart!),b=DateTime.tryParse(widget.initialEnd!);
      if(a!=null&&b!=null)range=DateTimeRange(start:a,end:b);}
    future=initialize();}
  @override void dispose(){search.dispose();super.dispose();}
  Future<dynamic> initialize()async{
    final responses=await Future.wait([widget.api.get('/classes'),widget.api.get('/violation-types')]);
    classes=responses[0] as List;types=responses[1] as List;
    if(widget.initialTypeName!=null){for(final t in types){if(t['name']==widget.initialTypeName)typeId=t['id'] as int;}}
    return fetch();
  }
  Future<dynamic> fetch()=>widget.api.get('/violations',{'student_code':search.text.trim(),
    'class_id':classId?.toString(),'type_id':typeId?.toString(),
    'start':range==null?null:DateFormat('yyyy-MM-dd').format(range!.start),
    'end':range==null?null:DateFormat('yyyy-MM-dd').format(range!.end),
    'offset':'$offset','limit':'50'});
  void apply(){setState((){offset=0;future=fetch();});}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Nhật ký vi phạm')),
    body:ListView(padding:const EdgeInsets.all(12),children:[
      TextField(controller:search,onSubmitted:(_)=>apply(),decoration:InputDecoration(labelText:'Tìm theo mã học sinh',suffixIcon:IconButton(onPressed:apply,icon:const Icon(Icons.search)))),gap,
      Row(children:[Expanded(child:DropdownButtonFormField<int>(value:classId,isExpanded:true,decoration:const InputDecoration(labelText:'Lớp'),
        items:[const DropdownMenuItem(value:null,child:Text('Tất cả')),...classes.map((c)=>DropdownMenuItem<int>(value:c['id'] as int,child:Text(c['name'] as String)))],
        onChanged:(v){classId=v;apply();})),const SizedBox(width:6),
        Expanded(child:DropdownButtonFormField<int>(value:typeId,isExpanded:true,decoration:const InputDecoration(labelText:'Loại vi phạm'),
          items:[const DropdownMenuItem(value:null,child:Text('Tất cả')),...types.map((t)=>DropdownMenuItem<int>(value:t['id'] as int,child:Text(t['name'] as String)))],
          onChanged:(v){typeId=v;apply();}))]),gap,
      OutlinedButton.icon(onPressed:()async{
        final r=await showDateRangePicker(context:context,firstDate:DateTime(2020),lastDate:DateTime(2040),initialDateRange:range);
        if(r!=null){range=r;apply();}
      },icon:const Icon(Icons.date_range),label:Text(range==null?'Lọc ngày':'${dateFormatter.format(range!.start)} – ${dateFormatter.format(range!.end)}')),
      FutureBuilder(future:future,builder:(context,s)=>loadState(s,done:(raw){
        final data=raw as Map;final items=data['items'] as List;final total=data['total'] as int;
        return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
          Padding(padding:const EdgeInsets.all(12),child:Text('$total bản ghi')),
          if(items.isEmpty)const Text('Không có vi phạm trong phạm vi lọc.'),
          for(final v in items)Card(child:ListTile(title:Text('${v['student_name']} – ${v['violation_type']}'),
            subtitle:Text('${v['class_name']}  •  ${dateUi(v['happened_on'] as String)}  •  ${v['recorder']}\n${v['note']??''}'),isThreeLine:true,
            onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StudentDetailScreen(api:widget.api,code:v['student_code'] as String))),
            trailing:Wrap(spacing:0,crossAxisAlignment:WrapCrossAlignment.center,children:[
              if((v['photo_count'] as int? ?? 0)>0)IconButton(tooltip:'Xem ảnh',icon:const Icon(Icons.photo_library_outlined),
                onPressed:()=>showViolationPhotos(context,widget.api,v as Map)),
              if(widget.api.canRecord && (v['photo_count'] as int? ?? 0)<3)IconButton(tooltip:'Bổ sung ảnh',icon:const Icon(Icons.add_a_photo_outlined),
                onPressed:()async{if(await addPhotoToExisting(context,widget.api,v as Map) && mounted)apply();}),
            ]))),
          Row(mainAxisAlignment:MainAxisAlignment.center,children:[
            IconButton(onPressed:offset>0?()=>setState((){offset=(offset-50).clamp(0,total).toInt();future=fetch();}):null,icon:const Icon(Icons.chevron_left)),
            Text(total==0?'0 bản ghi':'${offset+1}–${offset+items.length} / $total'),
            IconButton(onPressed:offset+50<total?()=>setState((){offset+=50;future=fetch();}):null,icon:const Icon(Icons.chevron_right)),
          ])
        ]);
      }))
    ]));
}

class ReportScreen extends StatefulWidget {
  final ThdApi api;final int revision;
  const ReportScreen({super.key,required this.api,required this.revision});
  @override State<ReportScreen> createState()=>_ReportScreenState();
}
class _ReportScreenState extends State<ReportScreen> {
  String? start,end;late Future<dynamic> future;bool exporting=false;
  @override void initState(){super.initState();reload();}
  @override void didUpdateWidget(covariant ReportScreen old){super.didUpdateWidget(old);if(old.revision!=widget.revision)reload();}
  void reload(){future=widget.api.get('/reports/weekly',{'start':start,'end':end});}
  Future<void> dates()async{
    final now=DateTime.now();final range=await showDateRangePicker(context:context,firstDate:DateTime(2020),lastDate:DateTime(2040),
      initialDateRange:DateTimeRange(start:DateTime.tryParse(start??'')??now,end:DateTime.tryParse(end??'')??now));
    if(range!=null)setState((){start=DateFormat('yyyy-MM-dd').format(range.start);end=DateFormat('yyyy-MM-dd').format(range.end);reload();});
  }
  Future<void> download(String extension)async{
    setState(()=>exporting=true);
    try{
      final params={'start':start,'end':end}..removeWhere((key,value)=>value==null);
      final query=params.entries.map((e)=>'${e.key}=${Uri.encodeComponent(e.value!)}').join('&');
      await widget.api.export('/reports/weekly.$extension${query.isNotEmpty?'?$query':''}','thd_report_${start??'current'}.$extension');
      if(mounted)showSuccess(context,'Đã tạo tệp báo cáo $extension');
    }catch(e){if(mounted)showError(context,e);}
    finally{if(mounted)setState(()=>exporting=false);}
  }
  @override Widget build(BuildContext context)=>ListView(padding:const EdgeInsets.all(16),children:[
    Text('Báo cáo theo khoảng ngày',style:Theme.of(context).textTheme.headlineSmall),gap,
    OutlinedButton.icon(onPressed:dates,icon:const Icon(Icons.date_range),label:Text(start==null?'Chọn khoảng ngày (mặc định Thứ Hai–Thứ Bảy)':'${dateUi(start)} – ${dateUi(end)}')),gap,
    FutureBuilder(future:future,builder:(context,s)=>loadState(s,done:(raw){
      final d=raw as Map;final rows=d['classes'] as List;
      return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        Card(child:Padding(padding:const EdgeInsets.all(18),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
          Text(d['school'] as String,style:const TextStyle(fontWeight:FontWeight.bold)),Text('Năm học ${d['school_year']}'),
          Text('${dateUi(d['start'] as String)} – ${dateUi(d['end'] as String)}'),gap,
          Text('${d['total']} lượt vi phạm',style:Theme.of(context).textTheme.headlineSmall),
        ]))),gap,
        Row(children:[Expanded(child:FilledButton.icon(onPressed:exporting?null:()=>download('pdf'),icon:const Icon(Icons.picture_as_pdf_outlined),label:const Text('Xuất PDF'))),
          const SizedBox(width:8),Expanded(child:OutlinedButton.icon(onPressed:exporting?null:()=>download('xlsx'),icon:const Icon(Icons.table_chart_outlined),label:const Text('Xuất Excel')))]),
        if(exporting)const LinearProgressIndicator(),gap,
        Text('Theo 11 loại vi phạm',style:Theme.of(context).textTheme.titleMedium),
        for(final e in (d['by_type'] as Map).entries)ListTile(dense:true,title:Text('${e.key}'),trailing:Text('${e.value}')),
        gap,Text('Theo lớp (${rows.length})',style:Theme.of(context).textTheme.titleMedium),
        for(final r in rows)Card(child:ExpansionTile(title:Text('${r['class_name']} – ${r['total']} lượt'),
          subtitle:Text(r['warning'] as String),children:[
            for(final e in (r['by_type'] as Map).entries)if(e.value!=0)ListTile(dense:true,title:Text('${e.key}'),trailing:Text('${e.value}')),
            if(r['total']==0)const ListTile(title:Text('Không có vi phạm trong kỳ')),
          ])),
      ]);
    }))
  ]);
}

class AdminScreen extends StatefulWidget {
  final ThdApi api;const AdminScreen({super.key,required this.api});
  @override State<AdminScreen> createState()=>_AdminScreenState();
}
class _AdminScreenState extends State<AdminScreen> {
  late Future<List<dynamic>> future;
  @override void initState(){super.initState();reload();}
  void reload(){future=Future.wait([widget.api.get('/admin/users'),widget.api.get('/classes'),widget.api.get('/admin/warning-rules'),widget.api.get('/admin/audit-logs'),widget.api.get('/school-years')]);}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Quản trị hệ thống')),
    body:FutureBuilder<List<dynamic>>(future:future,builder:(context,s)=>loadState(s,done:(raw){
      final data=raw as List;final users=data[0] as List;final classes=data[1] as List;final rules=data[2] as List;final audits=data[3] as List;final years=data[4] as List;
      return ListView(padding:const EdgeInsets.all(16),children:[
        Text('Năm học và lớp',style:Theme.of(context).textTheme.titleLarge),gap,
        for(final year in years)Card(child:ListTile(title:Text(year['name'] as String),
          subtitle:Text(year['active']?'Năm học đang sử dụng':'Chưa kích hoạt'),
          trailing:year['active']?const Icon(Icons.check_circle,color:Colors.green):TextButton(
            onPressed:()async{final done=await activateSchoolYear(context,widget.api,year);if(done && mounted)setState(reload);},
            child:const Text('Kích hoạt')))),
        Wrap(spacing:8,children:[OutlinedButton.icon(onPressed:()async{
          final done=await createSchoolYear(context,widget.api);if(done && mounted)setState(reload);
        },icon:const Icon(Icons.add),label:const Text('Thêm năm học')),
          OutlinedButton.icon(onPressed:()async{final done=await createClass(context,widget.api,years);if(done && mounted)setState(reload);},
            icon:const Icon(Icons.meeting_room_outlined),label:const Text('Thêm lớp'))]),gap,
        Text('Tài khoản (${users.length})',style:Theme.of(context).textTheme.titleLarge),gap,
        FilledButton.icon(onPressed:()async{final done=await createUser(context,widget.api,classes);if(done && mounted)setState(reload);},
          icon:const Icon(Icons.person_add),label:const Text('Tạo tài khoản và phân lớp')),
        for(final u in users)Card(child:ListTile(title:Text(u['display_name'] as String),subtitle:Text('${u['username']}  •  ${u['role']}  •  Lớp: ${(u['class_ids'] as List).length}'),
          trailing:Text(u['is_active']?'Đang dùng':'Đã khóa'),onTap:()async{
            final done=await manageUser(context,widget.api,u,classes);
            if(done && mounted)setState(reload);
          })),
        gap,Text('Ngưỡng cảnh báo',style:Theme.of(context).textTheme.titleLarge),
        const Text('Thay đổi ngưỡng sẽ tính lại toàn bộ cảnh báo khi mở trang. Hãy đánh giá tác động trước khi áp dụng.'),
        for(final r in rules)Card(child:ListTile(title:Text(r['label'] as String),subtitle:Text('${r['min_count']} – ${r['max_count']??'không giới hạn'}'))),
        OutlinedButton.icon(onPressed:()async{
          final done=await editWarningRules(context,widget.api,rules);
          if(done && mounted)setState(reload);
        },icon:const Icon(Icons.tune),label:const Text('Chỉnh ngưỡng cảnh báo')),
        gap,Text('Nhật ký kiểm toán gần đây',style:Theme.of(context).textTheme.titleLarge),
        for(final a in audits.take(30))ListTile(dense:true,title:Text(a['action'] as String),subtitle:Text('${a['entity']} #${a['entity_id']}  •  ${a['at']}')),
      ]);
    })));
}

Future<bool> createUser(BuildContext parent,ThdApi api,List<dynamic> classes)async{
  final username=TextEditingController(),name=TextEditingController(),password=TextEditingController();
  String role='homeroom';final assigned=<int>{};bool saving=false;
  final result=await showDialog<bool>(context:parent,builder:(context)=>StatefulBuilder(builder:(context,update)=>AlertDialog(
    title:const Text('Tạo tài khoản'),content:SizedBox(width:500,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
      TextField(controller:username,decoration:const InputDecoration(labelText:'Tên đăng nhập')),gap,
      TextField(controller:name,decoration:const InputDecoration(labelText:'Tên hiển thị')),gap,
      TextField(controller:password,obscureText:true,decoration:const InputDecoration(labelText:'Mật khẩu tạm (≥12 ký tự)')),gap,
      DropdownButtonFormField<String>(value:role,decoration:const InputDecoration(labelText:'Vai trò'),
        items:const [DropdownMenuItem(value:'admin',child:Text('Quản trị viên')),
          DropdownMenuItem(value:'leadership',child:Text('Ban giám hiệu / Đức dục')),
          DropdownMenuItem(value:'homeroom',child:Text('Giáo viên chủ nhiệm')),
          DropdownMenuItem(value:'recorder',child:Text('Giáo viên trực / nhập liệu'))],onChanged:(v)=>update(()=>role=v??role)),
      gap,const Text('Các lớp được phân công:'),
      ...classes.map((c)=>CheckboxListTile(dense:true,title:Text(c['name'] as String),value:assigned.contains(c['id']),
        onChanged:(v)=>update((){if(v==true)assigned.add(c['id'] as int);else assigned.remove(c['id']);}))),
    ]))),actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('Đóng')),
      FilledButton(onPressed:saving?null:()async{
        update(()=>saving=true);
        try{
          await api.post('/admin/users',{'username':username.text.trim(),'display_name':name.text.trim(),
            'password':password.text,'role':role,'class_ids':assigned.toList()});
          if(context.mounted)Navigator.pop(context,true);
        }catch(e){if(context.mounted)showError(context,e);update(()=>saving=false);}
      },child:const Text('Tạo tài khoản'))]
  )));
  username.dispose();name.dispose();password.dispose();return result??false;
}

Future<bool> manageUser(BuildContext parent,ThdApi api,dynamic user,List<dynamic> classes)async{
  final display=TextEditingController(text:user['display_name'] as String);
  final password=TextEditingController();String role=user['role'] as String;bool active=user['is_active'] as bool;
  final assigned=<int>{...(user['class_ids'] as List).cast<int>()};
  final result=await showDialog<bool>(context:parent,builder:(context)=>StatefulBuilder(builder:(context,update)=>AlertDialog(
    title:Text('Sửa ${user['username']}'),content:SizedBox(width:500,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
      TextField(controller:display,decoration:const InputDecoration(labelText:'Tên hiển thị')),gap,
      SwitchListTile(title:const Text('Tài khoản hoạt động'),value:active,onChanged:(v)=>update(()=>active=v)),
      DropdownButtonFormField<String>(value:role,decoration:const InputDecoration(labelText:'Vai trò'),
        items:const [DropdownMenuItem(value:'admin',child:Text('Quản trị viên')),DropdownMenuItem(value:'leadership',child:Text('Ban giám hiệu / Đức dục')),
          DropdownMenuItem(value:'homeroom',child:Text('GVCN')),DropdownMenuItem(value:'recorder',child:Text('Giáo viên trực'))],onChanged:(v)=>update(()=>role=v??role)),gap,
      TextField(controller:password,obscureText:true,decoration:const InputDecoration(labelText:'Đặt lại mật khẩu (để trống nếu giữ nguyên)')),gap,
      const Text('Phân quyền lớp:'),...classes.map((c)=>CheckboxListTile(dense:true,title:Text(c['name'] as String),value:assigned.contains(c['id']),
        onChanged:(v)=>update((){if(v==true)assigned.add(c['id'] as int);else assigned.remove(c['id']);})))
    ]))),actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('Đóng')),
      FilledButton(onPressed:()async{
        try{await api.patch('/admin/users/${user['id']}',{
          'display_name':display.text.trim(),'role':role,'is_active':active,
          'class_ids':assigned.toList(),if(password.text.isNotEmpty)'password':password.text});
          if(context.mounted)Navigator.pop(context,true);
        }catch(e){if(context.mounted)showError(context,e);}
      },child:const Text('Lưu thay đổi'))]
  )));
  display.dispose();password.dispose();return result??false;
}

Future<bool> editWarningRules(BuildContext parent,ThdApi api,List<dynamic> rules)async{
  final mins=rules.map((r)=>TextEditingController(text:'${r['min_count']}')).toList();
  final maxs=rules.map((r)=>TextEditingController(text:r['max_count']?.toString()??'')).toList();
  final result=await showDialog<bool>(context:parent,builder:(context)=>AlertDialog(title:const Text('Thay đổi ngưỡng cảnh báo'),
    content:SizedBox(width:500,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
      const Text('Khoảng phải liên tục từ 0, không chồng lấn. Mức cuối không giới hạn.'),gap,
      for(var i=0;i<rules.length;i++)Card(child:Padding(padding:const EdgeInsets.all(10),child:Column(children:[
        Text(rules[i]['label'] as String),Row(children:[Expanded(child:TextField(controller:mins[i],keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Từ'))),
          const SizedBox(width:8),Expanded(child:TextField(controller:maxs[i],enabled:i!=rules.length-1,keyboardType:TextInputType.number,
            decoration:const InputDecoration(labelText:'Đến')))])
      ])))
    ]))),actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('Bỏ qua')),
      FilledButton(onPressed:()async{
        final updated=<Map<String,dynamic>>[];
        for(var i=0;i<rules.length;i++){
          final min=int.tryParse(mins[i].text.trim()),max=i==rules.length-1?null:int.tryParse(maxs[i].text.trim());
          if(min==null || (i!=rules.length-1&&max==null)){showError(context,const ApiException(422,'Ngưỡng phải là số nguyên hợp lệ'));return;}
          updated.add({'min_count':min,'max_count':max,'label':rules[i]['label'],'recommendation':rules[i]['recommendation']});
        }
        try{await api.put('/admin/warning-rules',updated);if(context.mounted)Navigator.pop(context,true);}
        catch(e){if(context.mounted)showError(context,e);}
      },child:const Text('Xác nhận thay đổi'))]
  ));
  for(final c in [...mins,...maxs]){c.dispose();}return result??false;
}

Future<bool> createSchoolYear(BuildContext parent,ThdApi api)async{
  final name=TextEditingController();
  final done=await showDialog<bool>(context:parent,builder:(ctx)=>AlertDialog(
    title:const Text('Thêm năm học'),content:TextField(controller:name,decoration:const InputDecoration(labelText:'Ví dụ: 2027-2028')),
    actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Đóng')),
      FilledButton(onPressed:()async{
        try{await api.post('/admin/school-years',{'name':name.text.trim()});if(ctx.mounted)Navigator.pop(ctx,true);}
        catch(e){if(ctx.mounted)showError(ctx,e);}
      },child:const Text('Thêm'))]));
  name.dispose();return done??false;
}

Future<bool> activateSchoolYear(BuildContext parent,ThdApi api,dynamic year)async{
  final yes=await showDialog<bool>(context:parent,builder:(ctx)=>AlertDialog(title:const Text('Chuyển năm học đang hoạt động?'),
    content:Text('Hệ thống sẽ hiển thị dữ liệu năm ${year['name']}. Cần phân lớp và cấp quyền lại cho giáo viên theo năm mới.'),
    actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Không')),
      FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Xác nhận'))]));
  if(yes!=true)return false;
  try{await api.post('/admin/school-years/${year['id']}/activate',{});return true;}
  catch(e){if(parent.mounted)showError(parent,e);return false;}
}

Future<bool> createClass(BuildContext parent,ThdApi api,List<dynamic> years)async{
  final name=TextEditingController();int grade=10;
  int? yearId=years.where((y)=>y['active']==true).isNotEmpty
    ?years.firstWhere((y)=>y['active']==true)['id'] as int:null;
  final done=await showDialog<bool>(context:parent,builder:(ctx)=>StatefulBuilder(builder:(ctx,refresh)=>AlertDialog(
    title:const Text('Thêm lớp học'),content:Column(mainAxisSize:MainAxisSize.min,children:[
      DropdownButtonFormField<int>(value:yearId,decoration:const InputDecoration(labelText:'Năm học'),
        items:years.map((y)=>DropdownMenuItem<int>(value:y['id'] as int,child:Text(y['name'] as String))).toList(),
        onChanged:(v)=>refresh(()=>yearId=v)),gap,
      DropdownButtonFormField<int>(value:grade,decoration:const InputDecoration(labelText:'Khối'),
        items:const [DropdownMenuItem(value:10,child:Text('10')),DropdownMenuItem(value:11,child:Text('11')),
          DropdownMenuItem(value:12,child:Text('12'))],onChanged:(v)=>refresh(()=>grade=v??grade)),gap,
      TextField(controller:name,decoration:const InputDecoration(labelText:'Tên lớp (ví dụ 10A9)')),
    ]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Đóng')),
      FilledButton(onPressed:()async{
        try{await api.post('/admin/classes',{'name':name.text.trim(),'grade':grade,'school_year_id':yearId});
          if(ctx.mounted)Navigator.pop(ctx,true);
        }catch(e){if(ctx.mounted)showError(ctx,e);}
      },child:const Text('Lưu lớp'))]
  )));
  name.dispose();return done??false;
}
