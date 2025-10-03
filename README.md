Azure DevOps Variable Group Builder

Bu proje, `appsettings.json` veya `web.config` dosyalarından otomatik olarak **Azure DevOps Variable Group** oluşturmayı kolaylaştıran bir araçtır.  
Manuel olarak tek tek değişken eklemek yerine, dosyanı yükle — gerisini bu araç senin için halletsin.

## Özellikler

- ✅ `.json` veya `.config` dosyasından otomatik değişken çıkarma  
- ✅ JSON veya XML formatı desteği  
- ✅ Değişkenleri yükledikten sonra arayüz üzerinden düzenleme imkanı  
- ✅ Azure DevOps REST API kullanarak otomatik Variable Group oluşturma  
- ✅ `isSecret` flag'i desteği (Azure DevOps’ta secret olarak eklenir)  
- 🐳 Docker ile kolay kurulum ve çalıştırma

---

## Arayüz

Uygulama, aşağıdaki gibi basit ama işlevsel bir web arayüzüne sahiptir:

<img width="1532" height="740" alt="image" src="https://github.com/user-attachments/assets/b7b1c352-ba66-46d1-9959-4667a072d544" />


Sol tarafta Azure DevOps bilgileriniz yer alır:
- **Organization**: Azure DevOps organizasyon adınız  
- **Project**: Hedef proje adı  
- **PAT Token**: Personal Access Token (gizli tutulur, kaydedilmez)  
- **Variable Group Name**: Oluşturulacak Variable Group adı  
- **Description**: Opsiyonel açıklama alanı

Sağ tarafta ise `.json` veya `.config` dosyanızı yükleyerek değişkenleri otomatik oluşturabilirsiniz.  
Yükledikten sonra, oluşan değişkenleri tabloda görebilir, düzenleyebilir veya silebilirsiniz.

---

## 🐳 Docker ile Hızlı Başlangıç

Projeyi local ortamınıza indirip Docker kullanarak birkaç adımda çalıştırabilirsiniz.

### 1. Kodu İndirin
```bash
git clone https://github.com/<kullanıcı-adınız>/<repo-adı>.git
cd <repo-adı>
