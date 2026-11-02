import 'dart:async';
import 'package:flutter/material.dart';
import 'api.dart';
import 'screens.dart';
import 'branding.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ThdApi();
  runApp(ThdApp(api: api));
  api.restore();
}

class ThdApp extends StatelessWidget {
  final ThdApi api;
  const ThdApp({super.key, required this.api});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'THĐ Student Discipline',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF135C8B)),
        scaffoldBackgroundColor: const Color(0xFFF4F7FA),
        appBarTheme: const AppBarTheme(backgroundColor: Color(0xFFF4F7FA)),
        inputDecorationTheme: InputDecorationTheme(border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
        cardTheme: CardThemeData(elevation: 0, color: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
      ),
      home: ListenableBuilder(listenable: api, builder: (context, _) {
        if (!api.ready) return const Scaffold(body: Center(child: CircularProgressIndicator()));
        return api.signedIn ? AppShell(api: api) : LoginScreen(api: api);
      }),
    );
  }
}

class LoginScreen extends StatefulWidget {
  final ThdApi api;
  const LoginScreen({super.key, required this.api});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final username = TextEditingController();
  final password = TextEditingController();
  bool busy = false;

  Future<void> editServer() async {
    final controller = TextEditingController(text: widget.api.baseUrl);
    try {
      final updated = await showDialog<String>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Cấu hình máy chủ của trường'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Chỉ nhập địa chỉ HTTPS do bộ phận CNTT nhà trường cấp.'),
              const SizedBox(height: 14),
              TextField(
                controller: controller,
                keyboardType: TextInputType.url,
                autocorrect: false,
                decoration: const InputDecoration(
                  labelText: 'Địa chỉ máy chủ',
                  hintText: 'https://nennep.truong.edu.vn',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Hủy')),
            FilledButton(onPressed: () => Navigator.pop(dialogContext, controller.text), child: const Text('Lưu')),
          ],
        ),
      );
      if (updated == null) return;
      await widget.api.configureServer(updated);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã lưu máy chủ. Hãy đăng nhập để tiếp tục.')),
      );
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      controller.dispose();
    }
  }
  @override void dispose(){username.dispose();password.dispose();super.dispose();}
  Future<void> submit() async {
    if (username.text.trim().isEmpty || password.text.isEmpty) return;
    if (!widget.api.hasServer) {
      showError(context, const ApiException(0, 'Cần cấu hình địa chỉ máy chủ HTTPS trước khi đăng nhập.'));
      return;
    }
    setState(() => busy = true);
    try {await widget.api.login(username.text.trim(), password.text);}
    catch (e) {if (mounted) showError(context,e);}
    finally {if (mounted) setState(() => busy = false);}
  }
  @override Widget build(BuildContext context) => Scaffold(body: SafeArea(child: Center(child: SingleChildScrollView(
    padding: const EdgeInsets.all(24),child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 450),child: Column(
      mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        const SchoolBranding(logoSize: 76, withSchoolName: true),
        const SizedBox(height:12),
        Text('THĐ Student Discipline',textAlign:TextAlign.center,style:Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight:FontWeight.bold)),
        const Text('Quản lý nền nếp học sinh',textAlign:TextAlign.center),
        const SizedBox(height:22),
        OutlinedButton.icon(
          onPressed: busy ? null : editServer,
          icon: Icon(widget.api.hasServer ? Icons.dns_outlined : Icons.settings_ethernet),
          label: Text(widget.api.hasServer ? 'Máy chủ: ${widget.api.baseUrl}' : 'Cấu hình máy chủ (bắt buộc)'),
        ),
        const SizedBox(height:18),
        TextField(controller:username,textInputAction:TextInputAction.next,decoration:const InputDecoration(labelText:'Tên đăng nhập',prefixIcon:Icon(Icons.person_outline))),
        const SizedBox(height:14),
        TextField(controller:password,obscureText:true,onSubmitted:(_) => submit(),decoration:const InputDecoration(labelText:'Mật khẩu',prefixIcon:Icon(Icons.lock_outline))),
        const SizedBox(height:20),
        FilledButton(onPressed:busy?null:submit,child:Padding(padding:const EdgeInsets.all(12),child:busy?const CircularProgressIndicator():const Text('Đăng nhập'))),
        const SizedBox(height:20),
        const Text('Chỉ dành cho tài khoản được nhà trường cấp. Dữ liệu lưu tập trung trên máy chủ nội bộ.',textAlign:TextAlign.center,style:TextStyle(fontSize:12,color:Colors.black54)),
      ]))))));
}

class AppShell extends StatefulWidget {
  final ThdApi api;
  const AppShell({super.key,required this.api});
  @override State<AppShell> createState()=> _AppShellState();
}

class _AppShellState extends State<AppShell> with WidgetsBindingObserver {
  int tab=0,revision=0;
  Timer? _refreshTimer;
  AppLifecycleState _lifecycle=AppLifecycleState.resumed;

  @override void initState(){
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Same PostgreSQL data as PWA. Only refresh read-only screens, never a draft entry.
    _refreshTimer=Timer.periodic(const Duration(seconds:30),(_){
      if(mounted && _lifecycle==AppLifecycleState.resumed && [0,3,4].contains(tab)) {
        setState(()=>revision++);
      }
    });
  }
  @override void didChangeAppLifecycleState(AppLifecycleState state){
    _lifecycle=state;
    if(state==AppLifecycleState.resumed && mounted) setState(()=>revision++);
  }
  @override void dispose(){
    _refreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
  @override Widget build(BuildContext context){
    final titles=['Trang chủ','Nhập vi phạm','Tra cứu','Cảnh báo','Báo cáo'];
    final screens=<Widget>[
      HomeScreen(api:widget.api,revision:revision),
      RecordScreen(api:widget.api,onSaved:(){setState((){revision++;tab=0;});}),
      SearchScreen(api:widget.api,revision:revision),
      WarningScreen(api:widget.api,revision:revision),
      ReportScreen(api:widget.api,revision:revision)
    ];
    return Scaffold(
      appBar:AppBar(title:Row(children:[const SchoolBranding(logoSize: 28),const SizedBox(width: 10),Flexible(child:Text(titles[tab],overflow:TextOverflow.ellipsis))]),actions:[
        IconButton(tooltip:'Tải lại',onPressed:()=>setState(()=>revision++),icon:const Icon(Icons.refresh)),
        PopupMenuButton<String>(tooltip:'Tài khoản',onSelected:(choice){
          if(choice=='logout')widget.api.logout();
          if(choice=='admin')Navigator.push(context,MaterialPageRoute(builder:(_)=>AdminScreen(api:widget.api)));
          if(choice=='journal')Navigator.push(context,MaterialPageRoute(builder:(_)=>JournalScreen(api:widget.api)));
        },itemBuilder:(_)=>[
          PopupMenuItem(enabled:false,child:Text(widget.api.displayName??'Người dùng')),
          const PopupMenuItem(value:'journal',child:Text('Nhật ký vi phạm')),
          if(widget.api.isAdmin)const PopupMenuItem(value:'admin',child:Text('Quản trị hệ thống')),
          const PopupMenuItem(value:'logout',child:Text('Đăng xuất')),
        ]),
      ]),
      body:IndexedStack(index:tab,children:screens),
      bottomNavigationBar:NavigationBar(selectedIndex:tab,onDestinationSelected:(i)=>setState(()=>tab=i),destinations:const [
        NavigationDestination(icon:Icon(Icons.dashboard_outlined),selectedIcon:Icon(Icons.dashboard),label:'Trang chủ'),
        NavigationDestination(icon:Icon(Icons.edit_note),label:'Nhập'),
        NavigationDestination(icon:Icon(Icons.search),label:'Tra cứu'),
        NavigationDestination(icon:Icon(Icons.warning_amber_outlined),label:'Cảnh báo'),
        NavigationDestination(icon:Icon(Icons.description_outlined),label:'Báo cáo'),
      ]),
    );
  }
}
