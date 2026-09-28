// Single-file Windows launcher. Runtime files are verified on every launch;
// only versioned application libraries are cached, never photographs.
using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using System.Drawing;
using System.Collections.Generic;

static class Launcher {
    static readonly string Root = Path.GetFullPath(Environment.GetEnvironmentVariable("AVGFACE_CACHE_DIR") ?? Path.Combine(Path.GetTempPath(), "AverageFaceGenerator"));
    static readonly string Cache = Path.Combine(Root, "runtime-" + BuildInfo.Id);
    static readonly Assembly Assembly = Assembly.GetExecutingAssembly();
    static string Hash(Stream stream) { using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
    static string SafePath(string root, string relative) {
        string path=Path.GetFullPath(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));
        if(!path.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)) throw new IOException("Invalid runtime path");
        return path;
    }
    static void NoLinks(string path, string root) {
        for(string current=path; current!=null; current=Path.GetDirectoryName(current)) {
            if((File.Exists(current)||Directory.Exists(current)) && (File.GetAttributes(current)&FileAttributes.ReparsePoint)!=0) throw new IOException("Runtime cache must not contain links");
            if(String.Equals(current,root,StringComparison.OrdinalIgnoreCase)) break;
        }
    }
    static bool Verify(string directory) {
        try {
            NoLinks(directory,Root);
            using(var reader=new StreamReader(Assembly.GetManifestResourceStream("runtime.manifest"),Encoding.UTF8)) {
                string line;
                while((line=reader.ReadLine())!=null) {
                    string[] fields=line.Split('\t');
                    string file=SafePath(directory,fields[2]); NoLinks(file,Root);
                    if(!File.Exists(file)||new FileInfo(file).Length!=Int64.Parse(fields[1])) return false;
                    using(var stream=File.OpenRead(file)) if(Hash(stream)!=fields[0]) return false;
                }
            }
            return true;
        } catch(IOException) { return false; } catch(UnauthorizedAccessException) { return false; }
    }
    static string Prepare(Action<int> progress) {
        Directory.CreateDirectory(Root); NoLinks(Root,Root);
        using(var gate=new Mutex(false,"Local\\AverageFaceGenerator-"+BuildInfo.Id)) {
            bool acquired=false;
            try {
                try { acquired=gate.WaitOne(TimeSpan.FromMinutes(3)); } catch(AbandonedMutexException) { acquired=true; }
                if(!acquired) throw new IOException("另一实例正在准备程序，请稍后重试。");
                if(Verify(Cache)) return Path.Combine(Cache,"AvgFaceApp.exe");
                string staging=SafePath(Root,"preparing-"+Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(staging);
                using(var payload=Assembly.GetManifestResourceStream("runtime.zip"))
                using(var zip=new ZipArchive(payload,ZipArchiveMode.Read)) {
                    int done=0;
                    foreach(var entry in zip.Entries) {
                        if(entry.Name.Length==0) continue;
                        string file=SafePath(staging,entry.FullName);
                        Directory.CreateDirectory(Path.GetDirectoryName(file));
                        using(var input=entry.Open()) using(var output=new FileStream(file,FileMode.CreateNew,FileAccess.Write)) input.CopyTo(output);
                        progress(++done*100/zip.Entries.Count);
                    }
                }
                if(!Verify(staging)) throw new IOException("运行库校验失败，请重新获取程序。");
                // Preserve a damaged cache rather than deleting possibly in-use files.
                if(Directory.Exists(Cache)) { NoLinks(Cache,Root); Directory.Move(Cache,SafePath(Root,"damaged-"+Guid.NewGuid().ToString("N"))); }
                Directory.Move(staging,Cache);
                return Path.Combine(Cache,"AvgFaceApp.exe");
            } finally { if(acquired) gate.ReleaseMutex(); }
        }
    }
    static string Quote(string value) {
        var result=new StringBuilder("\""); int slashes=0;
        foreach(char c in value) {
            if(c=='\\') { slashes++; continue; }
            if(c=='"') result.Append('\\',slashes*2+1).Append(c);
            else result.Append('\\',slashes).Append(c);
            slashes=0;
        }
        return result.Append('\\',slashes*2).Append('"').ToString();
    }
    [STAThread] static int Main(string[] args) {
        try {
            string executable=null;
            bool automated=Array.IndexOf(args,"--self-test")>=0 || Array.IndexOf(args,"--startup-test")>=0;
            if(Directory.Exists(Cache)||automated) executable=Prepare(delegate(int p) {});
            else {
                Application.EnableVisualStyles();
                using(var splash=new Form()) {
                    splash.Icon=Icon.ExtractAssociatedIcon(Assembly.Location);
                    splash.Text="平均脸生成器 " + BuildInfo.Version; splash.ClientSize=new Size(400,140);
                    splash.StartPosition=FormStartPosition.CenterScreen; splash.FormBorderStyle=FormBorderStyle.FixedDialog;
                    splash.ControlBox=false; splash.BackColor=Color.FromArgb(248,250,254);
                    var title=new Label { Text="正在准备首次启动…", AutoSize=true, Location=new Point(28,30), Font=new Font("Microsoft YaHei UI",13), ForeColor=Color.FromArgb(32,42,58) };
                    var track=new Panel { Location=new Point(28,95), Size=new Size(344,5), BackColor=Color.FromArgb(225,230,240) };
                    var fill=new Panel { Location=new Point(0,0), Size=new Size(0,5), BackColor=Color.FromArgb(73,104,232) };
                    track.Controls.Add(fill); splash.Controls.Add(title); splash.Controls.Add(track);
                    Exception failure=null;
                    splash.Shown+=delegate {
                        new Thread(delegate() {
                            try { executable=Prepare(delegate(int p) { splash.BeginInvoke((Action)delegate { fill.Width=344*p/100; }); }); }
                            catch(Exception error) { failure=error; }
                            finally { splash.BeginInvoke((Action)delegate { splash.Close(); }); }
                        }) { IsBackground=true }.Start();
                    };
                    Application.Run(splash);
                    if(failure!=null) throw failure;
                }
            }
            var quoted=new List<string>(); foreach(var arg in args) quoted.Add(Quote(arg));
            var info=new ProcessStartInfo(executable,String.Join(" ",quoted.ToArray())) { UseShellExecute=false, WorkingDirectory=Environment.CurrentDirectory };
            using(var process=Process.Start(info)) { process.WaitForExit(); return process.ExitCode; }
        } catch(Exception error) {
            for(int i=0;i+1<args.Length;i++) if(args[i]=="--self-test"||args[i]=="--startup-test") { File.WriteAllText(args[i+1],error.ToString()); return 1; }
            MessageBox.Show(error.Message,"平均脸生成器",MessageBoxButtons.OK,MessageBoxIcon.Error); return 1;
        }
    }
}
