import os
from dotenv import load_dotenv
from pathlib import Path
import logging
import logging.config

from backend.lib.cloudflareWorker import CloudflareWorker
from lightrag import QueryParam, LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import logger, set_verbose_debug, EmbeddingFunc

# Configuration
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / '.env')
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "INSERT API KEY")
API_BASE_URL = os.getenv("CLOUDFLARE_API_BASE_URL", "INSERT YOUR API BASE URL")
LLM_MODEL = os.getenv("LLM_MODEL", "INSERT YOUR LLM MODEL HERE")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "INSERT YOUR EMBEDDING MODEL")
WORKING_DIR = f'.{os.getenv("WORKING_DIR", "INSERT YOUR WORKING DIR")}' # working directory located one level above this file's directory, supposedly.
USER_DATA_DIR = os.getenv("USER_DATA_IDR", "INSERT YOUR USER DATA DIR HERE")
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this")

def configure_logging():
    """Configure logging for the application"""

    # Reset any existing handlers to ensure clean configuration
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "lightrag"]:
        logger_instance = logging.getLogger(logger_name)
        logger_instance.handlers = []
        logger_instance.filters = []

    # Get log directory path from environment variable or use current directory
    log_dir = os.getenv("LOG_DIR", os.getcwd())
    log_file_path = os.path.abspath(os.path.join(log_dir, "lightrag_cloudflare_worker_demo.log"))

    print(f"\nLightRAG compatible demo log file: {log_file_path}\n")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # Get log file max size and backup count from environment variables
    log_max_bytes = int(os.getenv("LOG_MAX_BYTES", 10485760))  # Default 10MB
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))  # Default 5 backups

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(levelname)s: %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
                "file": {
                    "formatter": "detailed",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_file_path,
                    "maxBytes": log_max_bytes,
                    "backupCount": log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "lightrag": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )

    # Set the logger level to INFO
    logger.setLevel(logging.INFO)
    # Enable verbose debug if needed
    set_verbose_debug(os.getenv("VERBOSE_DEBUG", "false").lower() == "true")

class MyLightRAG:
    def __init__(self):
        configure_logging()
        print("Initializing LightRAG\n=======")
        print("Initializing Cloudflare\n=======")
        self.cloudflare_worker = CloudflareWorker(
            cloudflare_api_key=CLOUDFLARE_API_KEY,
            api_base_url=API_BASE_URL,
            embedding_model_name=EMBEDDING_MODEL,
            llm_model_name=LLM_MODEL,
        )
        print("Initializing LightRAG Class\n=======")
        self.rag = LightRAG(
            working_dir=WORKING_DIR,
            max_parallel_insert=2,
            llm_model_func=self.cloudflare_worker.query,
            llm_model_name=LLM_MODEL,
            llm_model_max_token_size=4080,
            embedding_func=EmbeddingFunc(
                embedding_dim=int(os.getenv("EMBEDDING_DIM", "1024")),
                max_token_size=int(os.getenv("MAX_EMBED_TOKENS", "2048")),
                func=lambda texts: self.cloudflare_worker.embedding_chunk(texts),
            ),
        )
        print("Finished initalizing LightRAG class\n=======")
    @classmethod
    async def create(cls):
        """Async factory method to safely initialize."""
        print("Initializing second phase LightRAG\n=======")
        instance = cls()
        await instance.rag.initialize_storages()
        await initialize_pipeline_status()
        print("Finished initializing second phase LightRAG\n=======")
        return instance

    async def createKG(self, book):
        print("Checking working directory existance\n=======")
        if not os.path.exists(WORKING_DIR):
            print("Working directory does not exist, creating it\n=======")
            os.mkdir(WORKING_DIR)
        else:
            print("Working Directory exists\n======")

        try:
            test_text = ["This is a test string for embedding."]
            embedding = await self.rag.embedding_func(test_text)
            print(f"Embedding dimension: {embedding.shape[1]}")
            print(f'Starting full insertion of test\nlogs:')
            await self.rag.ainsert(book)
            print(f'Finished insertion of text')

        except Exception as e:
            print(f"Error in createKG: {e}")

    async def query(self, query, mode):
        ALLOWED_MODES = {'hybrid', 'local', 'naive', 'global'}

        if mode.lower() in ALLOWED_MODES:
            resp = await self.rag.aquery(
                query=query,
                param=QueryParam(mode=mode.lower(), stream=True)
            )
            return resp

        return 'Invalid query mode'

# import asyncio
# async def main():
#     myLightRAG = await MyLightRAG.create()
#     await myLightRAG.createKG(book='''
# 3 BẢO ĐẢM AN TOÀN CHO NGƯỜI
# 3.1 	Quy định chung
# 3.1.1 	Các yêu cầu trong phần này nhằm bảo đảm:
# - Thoát nạn cho người kịp thời và không bị cản trở;
# - Cứu người bị tác động của các yếu tố nguy hiểm của đám cháy;
# - Bảo vệ người trên đường thoát nạn tránh khỏi những tác động của các yếu tố nguy hiểm của đám cháy.
# 3.1.2 	Thoát nạn là quá trình tự di chuyển có tổ chức của người ra bên ngoài từ các gian phòng, nơi các yếu tố nguy hiểm của đám cháy có thể tác động lên họ. Thoát nạn còn là sự di chuyển không tự chủ của nhóm người ít có khả năng vận động, do các nhân viên phục vụ thực hiện. Thoát nạn được thực hiện theo các đường thoát nạn qua các lối ra thoát nạn.
# 3.1.3 	Cứu nạn là sự di chuyển cưỡng bức của người ra bên ngoài khi họ bị các yếu tố nguy hiểm của đám cháy tác động hoặc khi xuất hiện nguy cơ trực tiếp của các tác động đó. Cứu nạn được thực hiện một cách tự chủ với sự trợ giúp của lực lượng chữa cháy hoặc nhân viên được huấn luyện chuyên nghiệp, bao gồm cả việc sử dụng các phương tiện cứu hộ, qua các lối ra thoát nạn và lối ra khẩn cấp.
# 3.1.4 	Việc bảo vệ người trên các đường thoát nạn phải được bảo đảm bằng tổ hợp các giải pháp bố trí mặt bằng - không gian, tiện nghi, kết cấu, kỹ thuật công trình và tổ chức.
# Các đường thoát nạn trong phạm vi gian phòng phải bảo đảm sự thoát nạn an toàn qua các lối ra thoát nạn từ gian phòng đó mà không tính đến các phương tiện bảo vệ chống khói và chữa cháy có trong gian phòng này.
# Việc bảo vệ đường thoát nạn ngoài phạm vi gian phòng phải được tính đến theo điều kiện bảo đảm thoát nạn an toàn cho người có kể đến tính nguy hiểm cháy theo công năng của các gian phòng trên đường thoát nạn, số người thoát nạn, bậc chịu lửa và cấp nguy hiểm cháy kết cấu của nhà, số lối ra thoát nạn từ một tầng và từ toàn bộ nhà.
# Trong các gian phòng và trên các đường thoát nạn ngoài phạm vi gian phòng phải hạn chế tính nguy hiểm cháy của vật liệu xây dựng thuộc các lớp bề mặt kết cấu (lớp hoàn thiện và ốp mặt) tùy thuộc vào tính nguy hiểm cháy theo công năng của gian phòng và nhà, có tính đến các giải pháp khác về bảo vệ đường thoát nạn.
# 3.1.5 	Khi bố trí thoát nạn từ các gian phòng và nhà thì không được tính đến các biện pháp và phương tiện dùng để cứu nạn, cũng như các lối ra không đáp ứng yêu cầu về lối ra thoát nạn quy định tại 3.2.1. 
# 3.1.6 	Không cho phép bố trí các gian phòng nhóm F5 hạng A hoặc hạng B dưới các gian phòng dùng cho hơn 50 người có mặt đồng thời; không bố trí các gian phòng nhóm F5 này trong các tầng hầm và tầng nửa hầm.
# Không cho phép bố trí các gian phòng nhóm F1.1, F1.2 và F1.3 trong các tầng hầm và tầng nửa hầm.
# 3.1.7 	Trong các nhà có từ 2 đến 3 tầng hầm, chỉ được phép bố trí phòng hút thuốc, các siêu thị và trung tâm thương mại, quán ăn, quán giải khát và các gian phòng công cộng khác nằm sâu hơn tầng hầm 1 khi có các giải pháp bảo đảm an toàn cháy bổ sung theo tài liệu chuẩn được áp dụng và được cơ quan quản lý nhà nước có thẩm quyền chấp thuận theo quy định tại 1.1.10.
# Đối với bệnh viện và trường phổ thông, chỉ cho phép bố trí các công năng chính từ tầng bán hầm hoặc tầng hầm 1 (trong trường hợp không có tầng bán hầm) trở lên. Tầng hầm 1 là tầng hầm trên cùng hoặc ngay sát tầng bán hầm.
# Tại tất cả các sàn tầng hầm, ít nhất phải có 1 lối vào buồng thang bộ thoát nạn đi qua sảnh ngăn khói được ngăn cách với các không gian xung quanh bằng tường ngăn cháy loại 2. Các cửa đi phải là loại có cơ cấu tự đóng.
# 3.1.8 	Để bảo đảm thoát nạn an toàn, phải phát hiện cháy và báo cháy kịp thời. 
# 3.1.9 	Để bảo vệ người thoát nạn, phải bảo vệ chống khói xâm nhập các đường thoát nạn của nhà và các phần nhà.
# Các yêu cầu cơ bản về bảo vệ chống khói cho nhà được quy định tại Phụ lục D.
# 3.1.10 	Các thiết bị điện của hệ thống bảo vệ chống cháy của nhà phải được cấp điện ưu tiên từ hai nguồn độc lập (một nguồn điện lưới và một nguồn máy phát điện dự phòng).
# CHÚ THÍCH: 	Đối với các thiết bị điện có nguồn dự phòng riêng (ví dụ bơm diezen, tủ chống cháy có ắc quy dự phòng) thì chỉ cần một nguồn điện lưới, nhưng nguồn dự phòng riêng này phải đảm bảo hoạt động bình thường khi có cháy.
# 3.1.11 	Hiệu quả của các giải pháp bảo đảm an toàn cho người khi cháy có thể được đánh giá bằng tính toán.
# 3.2 	Lối ra thoát nạn và lối ra khẩn cấp
# 3.2.1 	Các lối ra được coi là lối ra thoát nạn nếu chúng:
# a) Dẫn từ các gian phòng ở tầng 1 ra ngoài theo một trong những cách sau:
# - Ra ngoài trực tiếp;
# - Qua hành lang;
# - Qua tiền sảnh (hay phòng chờ);
# - Qua buồng thang bộ;
# - Qua hành lang và tiền sảnh (hay phòng chờ);
# - Qua hành lang và buồng thang bộ.
# b) Dẫn từ các gian phòng của tầng bất kỳ, trừ tầng 1, vào một trong các nơi sau:
# - Trực tiếp vào buồng thang bộ hay tới cầu thang bộ loại 3;
# - Vào hành lang dẫn trực tiếp vào buồng thang bộ hay tới cầu thang bộ loại 3;
# - Vào phòng sử dụng chung (hay phòng chờ) có lối ra trực tiếp dẫn vào buồng thang bộ hoặc tới cầu thang bộ loại 3;
# - Vào hành lang bên của nhà có chiều cao PCCC dưới 28 m dẫn trực tiếp vào cầu thang bộ loại 2;
# - Ra mái có khai thác sử dụng, hoặc ra một khu vực riêng của mái dẫn tới cầu thang bộ loại 3.
# c) Dẫn vào gian phòng liền kề (trừ gian phòng nhóm F5 hạng A hoặc B) trên cùng tầng mà từ gian phòng này có các lối ra như được nêu tại 3.2.1 a, b). Lối ra dẫn vào gian phòng hạng A hoặc B được phép coi là lối ra thoát nạn nếu nó dẫn từ gian phòng kỹ thuật không có người làm việc thường xuyên mà chỉ dùng để phục vụ các gian phòng hạng A hoặc B nêu trên.
# d) Các lối ra đáp ứng quy định tại 3.2.2 và các lối ra thoát nạn khác được quy định cụ thể trong quy chuẩn này.
# CHÚ THÍCH: 	Trong trường hợp sử dụng cầu thang bộ loại 3 để thoát nạn cần có tính toán thoát nạn phù hợp với Phụ lục G. 
# 3.2.2 	Các lối ra từ các tầng hầm và tầng nửa hầm, về nguyên tắc, là lối ra thoát nạn khi chúng thoát trực tiếp ra ngoài và được ngăn cách với các buồng thang bộ chung của nhà (xem Hình I.1, Phụ lục I).
# Các lối ra sau đây cũng được coi là lối ra thoát nạn:
# a) Các lối ra từ các tầng hầm đi qua các buồng thang bộ chung có lối đi riêng ra bên ngoài được ngăn cách với phần còn lại của buồng thang bộ bằng vách đặc ngăn cháy loại 1 (xem Hình I.2, Phụ lục I);
# b) Các lối ra từ các tầng hầm và tầng nửa hầm có bố trí các gian phòng hạng C1 đến C4, D, E, đi vào các gian phòng hạng C1 đến C4, D, E và vào tiền sảnh nằm trên tầng một của nhà nhóm F5;
# c) Các lối ra từ phòng chờ, phòng gửi đồ, phòng hút thuốc và phòng vệ sinh ở các tầng hầm hoặc tầng nửa hầm của nhà nhóm F2, F3 và F4 đi vào tiền sảnh của tầng 1 theo các cầu thang bộ riêng loại 2. Trong trường hợp này thì phải bảo đảm các yêu cầu sau:
# - Tiền sảnh phải được ngăn cách với các hành lang và gian phòng lân cận bằng các vách ngăn cháy không nhỏ hơn loại 1;
# - Các gian phòng tầng 1 và các tầng trên phải có đường thoát nạn không đi qua tiền sảnh này (trừ các gian phòng nằm trong tiền sảnh);
# - Vật liệu hoàn thiện các phòng chờ, phòng gửi đồ, phòng hút thuốc và phòng vệ sinh ở các tầng hầm hoặc tầng nửa hầm phải thỏa mãn yêu cầu đối với các gian phòng chung theo Phụ lục B;
# - Phòng gửi đồ phải có số lối ra thoát nạn thỏa mãn yêu cầu của quy chuẩn này, không tính lối ra thoát nạn theo cầu thang bộ loại 2 nêu trên.
# d) Các cửa mở quay có bản lề trên cửa ra vào dành cho phương tiện vận tải đường sắt hoặc đường bộ.
# Cho phép bố trí khoang đệm tại lối ra ngoài trực tiếp từ nhà, từ tầng hầm và tầng nửa hầm.
# 3.2.3 	Các lối ra không được coi là lối ra thoát nạn nếu trên lối ra này có đặt cửa có cánh mở kiểu trượt hoặc xếp, cửa cuốn, cửa quay.
# Các cửa đi có cánh mở ra (cửa bản lề) nằm trong các cửa nói trên được coi là lối ra thoát nạn nếu được thiết kế theo đúng yêu cầu quy định.
# 3.2.4 	Số lượng và chiều rộng của các lối ra thoát nạn từ các gian phòng, các tầng và các nhà được xác định theo số lượng người thoát nạn lớn nhất có thể đi qua chúng và khoảng cách giới hạn cho phép từ chỗ xa nhất có thể có người (sinh hoạt, làm việc) tới lối ra thoát nạn gần nhất. 
# CHÚ THÍCH 1: 	Số lượng người thoát nạn lớn nhất từ các không gian khác nhau của nhà hoặc phần nhà được xác định theo G.3, Phụ lục G.
# CHÚ THÍCH 2: 	Ngoài các yêu cầu chung được nêu trong quy chuẩn này, yêu cầu cụ thể về số lượng và chiều rộng của các lối ra thoát nạn được nêu trong tài liệu chuẩn cho từng loại công trình. Phụ lục G nêu một số quy định cụ thể cho các nhóm nhà thường gặp.
# Các phần nhà có công năng khác nhau và được ngăn chia bởi các bộ phận ngăn cháy thì phải có các lối ra thoát nạn độc lập, trừ các trường hợp được quy định cụ thể trong quy chuẩn này. 
# Các phần nhà có công năng khác nhau và được ngăn chia bởi các bộ phận ngăn cháy thành các khoang cháy trong nhà có nhiều công năng phải có các lối ra thoát nạn riêng từ mỗi tầng. Cho phép không quá 50% lối ra thoát nạn dẫn vào khoang cháy lân cận (trừ lối ra thoát nạn dẫn vào khoang cháy nhóm F5). Riêng phần nhà nhóm F5 phải có lối ra thoát nạn riêng.
# 3.2.5 	Các gian phòng sau phải có không ít hơn hai lối ra thoát nạn:
# a) Các gian phòng nhóm F1.1 có mặt đồng thời hơn 15 người;
# b) Các gian phòng trong các tầng hầm và tầng nửa hầm có mặt đồng thời hơn 15 người; riêng các gian phòng trong tầng hầm và tầng nửa hầm có từ 6 đến 15 người có mặt đồng thời thì cho phép một trong hai lối ra là lối ra khẩn cấp theo các yêu cầu tại đoạn d) của 3.2.13; 
# c) Các gian phòng có mặt đồng thời từ 50 người trở lên;
# d) Các gian phòng (trừ các gian phòng nhóm F5) có mặt đồng thời dưới 50 người (bao gồm cả tầng khán giả ở trên cao hoặc ban công khán phòng) với khoảng cách dọc theo lối đi từ chỗ xa nhất có người đến lối ra thoát nạn vượt quá 25 m. Khi có các lối thoát nạn thông vào gian phòng đang xét từ các gian phòng bên cạnh với số lượng trên 5 người có mặt ở mỗi phòng bên cạnh, thì khoảng cách trên phải bao gồm độ dài đường thoát nạn cho người từ các gian phòng bên cạnh đó;
# e) Các gian phòng có tổng số người có mặt trong đó và trong các gian liền kề có lối thoát nạn chỉ đi vào gian phòng đang xét từ 50 người trở lên;
# f) Các gian phòng nhóm F5 hạng A hoặc B có số người làm việc trong ca đông nhất lớn hơn 5 người, hạng C - khi số người làm việc trong ca đông nhất lớn hơn 25 người hoặc có diện tích lớn hơn 1 000 m2;
# g) Các sàn công tác hở và các sàn dành cho người vận hành và bảo dưỡng thiết bị trong các gian phòng nhóm F5 có diện tích lớn hơn 100 m2 - đối với các gian phòng thuộc hạng A và B hoặc lớn hơn 400 m2 - đối với các gian phòng thuộc các hạng khác.
# Nếu gian phòng phải có từ 2 lối ra thoát nạn trở lên thì cho phép bố trí không quá 50% số lượng lối ra thoát nạn của gian phòng đó đi qua một gian phòng liền kề, với điều kiện gian phòng liền kề đó cũng phải có lối ra thoát nạn tuân thủ quy định của quy chuẩn này và các tài liệu chuẩn tương ứng cho gian phòng đó.
# 3.2.6 	Số lượng lối ra thoát nạn của tầng nhà
# 3.2.6.1 	Các tầng nhà sau đây phải có không ít hơn hai lối ra thoát nạn:
# a) Các tầng của nhà thuộc các nhóm F1.1; F1.2; F2.1; F2.2; F3; F4;
# b) Các tầng nhà với số lượng người từ 50 trở lên;
# c) Các tầng của nhà nhóm F1.3 khi tổng diện tích các căn hộ trên một tầng lớn hơn 500 m2 (đối với các nhà đơn nguyên thì tính diện tích trên một tầng của đơn nguyên). Trường hợp tổng diện tích các căn hộ trên một tầng nhỏ hơn hoặc bằng 500 m2 và khi chỉ có một lối ra thoát nạn từ một tầng, thì từ mỗi căn hộ ở độ cao lớn hơn 15 m, ngoài lối ra thoát nạn, phải có một lối ra khẩn cấp theo quy định tại 3.2.13;
# d) Các tầng của nhà nhóm F5, hạng A hoặc B khi số người làm việc trong ca đông nhất lớn hơn 5 người, hạng C khi số người làm việc trong ca đông nhất lớn hơn 25 người;
# e) Các tầng hầm và nửa hầm có diện tích lớn hơn 300 m2 hoặc dùng cho hơn 15 người có mặt đồng thời.
# 3.2.6.2 	f (trừ các nhà có bậc chịu lửa V):
# a) Từ mỗi tầng (hoặc từ một phần của tầng được ngăn cách khỏi các phần khác của tầng bằng các bộ phận ngăn cháy) có nhóm nguy hiểm cháy theo công năng F1.2, F1.4, F2 (trừ hộp đêm, vũ trường, quán bar, phòng hát, nhà kinh doanh karaoke; và các nhà kinh doanh dịch vụ tương tự), F3, F4.2, F4.3 và F4.4, khi thỏa mãn đồng thời các điều kiện sau:
# - Đối với nhà có chiều cao PCCC không quá 15 m thì diện tích mỗi tầng đang xét không được lớn hơn 300 m2. Đối với nhà có chiều cao PCCC từ trên 15 m đến 21 m thì diện tích mỗi tầng đang xét không được lớn hơn 200 m2;
# - Toàn bộ nhà được bảo vệ bằng hệ thống chữa cháy tự động sprinkler;
# - Số người lớn nhất trên mỗi tầng không vượt quá 20 người;
# - Đối với nhà trên 3 tầng hoặc có chiều cao PCCC lớn hơn 9 m: có trang bị cửa đi ngăn cháy loại 2 trên lối ra thoát nạn từ mỗi tầng đi vào buồng thang bộ thoát nạn. 
# - Đối với nhà từ 3 tầng trở xuống hoặc có chiều cao PCCC từ 9 m trở xuống: được sử dụng cầu thang bộ loại 2 thay thế cho buồng thang bộ nêu trên khi đảm bảo điều kiện người trong nhà có thể thoát ra ban công thoáng hoặc sân thượng thoáng khi có cháy (trừ các biệt thự, villa, cơ sở nghỉ dưỡng theo quy định riêng dưới đây).
# CHÚ THÍCH:	Ban công thoáng hoặc sân thượng thoáng nghĩa là hở ra ngoài trời và bộ phận bao che (nếu có) phải bảo đảm cho việc thoát nạn, cứu nạn dễ dàng khi lực lượng chữa cháy tiếp cận.
# Đối với các biệt thự, villa, cơ sở nghỉ dưỡng không cao quá 3 tầng thuộc nhóm F1.2, cho phép thay thế các loại buồng thang bộ nêu trên bằng cầu thang bộ loại 2, khi bảo đảm được đồng thời các điều kiện sau:
# - Diện tích mỗi tầng không quá 200 m2, chiều cao PCCC không quá 9 m và tổng số người sử dụng không quá 15 người;
# - Nhà có tối thiểu một lối ra thoát nạn trực tiếp ra ngoài hoặc ra cầu thang bộ loại 3;
# - Để thoát ra ngoài theo cầu thang bộ loại 2 chỉ cần lên hoặc xuống tối đa 1 tầng. Trường hợp phải xuống 2 tầng mới thoát được ra ngoài thì mỗi phòng có thể sử dụng để ngủ phải có không ít hơn một cửa sổ đặt ở cao độ không quá 1 m so với sàn và có lối thoát trực tiếp vào hành lang hoặc phòng chung có cửa ra ban công. Cao độ đặt các cửa sổ và ban công nêu trên không được quá 7 m so với mặt đất. Trường hợp các cửa sổ và ban công này đặt ở cao độ quá 7 m cho đến tối đa 9 m thì mỗi cửa sổ và ban công phải được trang bị thêm thiết bị thoát nạn khẩn cấp để bảo đảm việc thoát nạn cho người an toàn từ trên cao (ví dụ thang kim loại, thang dây); 
# b) Từ các tầng kỹ thuật hoặc khu vực để các thiết bị kỹ thuật có diện tích không quá 300 m2. Trường hợp tầng có khu vực kỹ thuật như trên, thì cứ mỗi 2 000 m2 diện tích còn lại phải bố trí thêm không ít hơn một lối ra thoát nạn (trường hợp diện tích còn lại nhỏ hơn 2 000 m2 cũng phải bố trí thêm không ít hơn một lối ra thoát nạn). Nếu tầng kỹ thuật hoặc khu vực kỹ thuật nằm dưới hầm thì lối ra thoát nạn phải riêng biệt với các lối ra khác của nhà và thoát thẳng ra ngoài. Nếu tầng kỹ thuật hoặc khu vực kỹ thuật nằm ở các tầng trên mặt đất thì cho phép bố trí các lối ra đi qua các buồng thang bộ chung, còn đối với nhà có các buồng thang bộ N1 - đi qua khoảng đệm của buồng thang bộ N1;
# c) Từ các tầng của nhà nhóm F1.3 với tổng diện tích các căn hộ trên tầng đó (đối với nhà có các đơn nguyên thì tính diện tích tầng trong đơn nguyên) từ trên 500 m2 đến 550 m2 và:
# - Khi cao độ của tầng trên cùng không quá 28 m - lối ra thoát nạn từ tầng đang xét vào buồng thang bộ thông thường, với điều kiện mỗi căn hộ được trang bị đầu báo cháy địa chỉ;
# - Khi cao độ của tầng trên cùng lớn hơn 28 m - lối ra thoát nạn từ tầng đang xét vào một buồng thang bộ không nhiễm khói N1 với điều kiện tất cả các phòng trong căn hộ (trừ khu vệ sinh, phòng tắm và khu phụ) được trang bị đầu báo cháy địa chỉ hoặc thiết bị chữa cháy tự động. 
# Đối với nhà nhóm F1.3 có chiều cao PCCC từ trên 28 m đến 50 m và tổng diện tích các căn hộ trên mỗi tầng đến 500 m2, cho phép thay buồng thang bộ loại N1 bằng buồng thang bộ loại N2, khi đáp ứng đồng thời các điều kiện sau: 1) Lối vào buồng thang bộ từ tất cả các tầng, bao gồm cả lối thông giữa buồng thang bộ và tiền sảnh, phải có khoang đệm ngăn cháy với áp suất dương khi có cháy; 2) Có một trong các thang máy của nhà được dành cho việc vận chuyển lực lượng chữa cháy; 3) Tất cả các phòng trong căn hộ (trừ khu vệ sinh, phòng tắm và khu phụ) được trang bị báo cháy địa chỉ hoặc hệ thống chữa cháy tự động; 4) Nhà được trang bị hệ thống âm thanh cảnh báo cháy (cho phép bố trí tại các hành lang chung giữa các căn hộ).
# CHÚ THÍCH: 	Diện tích căn hộ bao gồm cả diện tích ban công và (hoặc) lô gia.
# d) Từ các tầng (hoặc một phần của tầng được ngăn cách khỏi các phần khác của tầng bằng các bộ phận ngăn cháy) thuộc nhóm nguy hiểm cháy theo công năng F4.1, khi thỏa mãn đồng thời các điều kiện sau:
# - Nhà có chiều cao PCCC không quá 9 m, diện tích tầng đang xét không quá 300 m2;
# - Tầng đang xét có hành lang bên dẫn vào cầu thang hở loại 2 hoặc buồng thang bộ, các gian phòng nhóm F4.1 có cửa ra hàng lang bên này. 
# 3.2.7 	Số lối ra thoát nạn từ một tầng không được ít hơn hai nếu tầng này có ít nhất một gian phòng có yêu cầu số lối ra thoát nạn không ít hơn hai. 
# Số lối ra thoát nạn từ một nhà không được ít hơn số lối ra thoát nạn từ bất kỳ tầng nào của nhà đó.
# 3.2.8 	Khi có từ hai lối ra thoát nạn trở lên, chúng phải được bố trí phân tán và khi tính toán khả năng thoát nạn của các lối ra cần giả thiết là đám cháy đã ngăn cản không cho người sử dụng thoát nạn qua một trong những lối ra đó. Các lối ra còn lại phải bảo đảm khả năng thoát nạn an toàn cho tất cả số người có trong gian phòng, trên tầng hoặc trong nhà đó (xem Hình I.3). 
# Khi một gian phòng, một phần nhà hoặc một tầng của nhà yêu cầu phải có từ 2 lối ra thoát nạn trở lên thì ít nhất hai trong số những lối ra thoát nạn đó phải được bố trí phân tán, đặt cách nhau một khoảng bằng hoặc lớn hơn một nửa chiều dài của đường chéo lớn nhất của mặt bằng gian phòng, phần nhà hoặc tầng nhà đó. Khoảng cách giữa hai lối ra thoát nạn được đo theo đường thẳng nối giữa hai cạnh gần nhất của chúng (xem Hình I.4 a), b), c)).
# Nếu nhà được bảo vệ toàn bộ bằng hệ thống chữa cháy tự động Sprinkler, thì khoảng cách này có thể giảm xuống còn 1/3 chiều dài đường chéo lớn nhất của mặt bằng các gian phòng trên (xem Hình I.4 d)).
# Khi có hai buồng thang thoát nạn nối với nhau bằng một hành lang trong thì khoảng cách giữa hai lối ra thoát nạn (cửa vào buồng thang thoát nạn) được đo dọc theo đường di chuyển theo hành lang đó (xem Hình I.5). Hành lang này phải được bảo vệ theo quy định tại 3.3.5.
# 3.2.9 	Chiều cao thông thủy của lối ra thoát nạn phải không nhỏ hơn 1,9 m, chiều rộng thông thủy không nhỏ hơn: 
# - 1,2 m - từ các gian phòng nhóm F1.1 khi số người thoát nạn lớn hơn 15 người, từ các gian phòng và nhà thuộc nhóm nguy hiểm cháy theo công năng khác có số người thoát nạn lớn hơn 50 người, ngoại trừ nhóm F1.3; 
# - 0,8 m - trong tất cả các trường hợp còn lại. 
# Chiều rộng của các cửa đi ra bên ngoài của buồng thang bộ cũng như của các cửa đi từ buồng thang bộ vào sảnh không được nhỏ hơn giá trị tính toán hoặc chiều rộng của bản thang được quy định tại 3.4.1.
# Trong mọi trường hợp, khi xác định chiều rộng của một lối ra thoát nạn phải tính đến dạng hình học của đường thoát nạn qua lỗ cửa hoặc cửa để bảo đảm không cản trở việc vận chuyển các cáng tải thương có người nằm trên. 
# Nếu sử dụng cửa hai cánh trên lối ra thoát nạn thì chiều rộng của lối ra thoát nạn chỉ được lấy bằng chiều rộng lối đi qua bên cánh mở, không được phép tính bên cánh đóng hoặc cánh cố định. Cửa hai cánh phải được lắp cơ cấu tự đóng sao cho các cánh được đóng lần lượt.
# Trong các nhà có chiều cao PCCC lớn hơn 28 m (trừ nhà nhóm F1.3 và F1.4), các cửa thoát nạn từ các hành lang chung mỗi tầng, từ sảnh chung, phòng chờ, tiền sảnh, buồng thang bộ (trừ cửa thoát nạn trực tiếp ra ngoài trời), phải là cửa chống cháy với giới hạn chịu lửa không thấp hơn EI 30.
# 3.2.10 	Các cửa của lối ra thoát nạn và các cửa khác trên đường thoát nạn phải được mở theo chiều lối thoát từ trong nhà ra ngoài.
# Không quy định chiều mở của các cửa đối với:
# - Các gian phòng nhóm F1.3 và F1.4;
# - Các gian phòng có mặt đồng thời không quá 15 người, ngoại trừ các gian phòng hạng A hoặc B;
# - Các phòng kho có diện tích không lớn hơn 200 m2 và không có người làm việc thường xuyên;
# - Các buồng vệ sinh;
# - Các lối ra dẫn vào các chiếu thang của các cầu thang bộ loại 3.
# 3.2.11 	Các cửa của các lối ra thoát nạn từ các hành lang tầng, không gian chung, phòng chờ, sảnh và buồng thang bộ phải mở được cửa tự do từ bên trong mà không cần chìa. Trong các nhà có chiều cao PCCC lớn hơn 15 m, các cánh cửa nói trên, ngoại trừ các cửa của căn hộ, phải là cửa đặc hoặc cửa với kính cường lực.
# Các cửa của lối ra thoát nạn từ các khu vực (gian phòng hay các hành lang) được bảo vệ chống khói cưỡng bức phải là cửa đặc được trang bị cơ cấu tự đóng và khe cửa phải được chèn kín. Các cửa này nếu cần để mở khi sử dụng thì phải được trang bị cơ cấu tự động đóng khi có cháy.
# Đối với các buồng thang bộ, các cửa ra vào phải có cơ cấu tự đóng và khe cửa phải được chèn kín. Các cửa trong buồng thang bộ mở trực tiếp ra ngoài cho phép không có cơ cấu tự đóng và không cần chèn kín khe cửa. Ngoại trừ những trường hợp được quy định riêng, cửa của buồng thang bộ phải bảo đảm là cửa ngăn cháy loại 1 đối với nhà có bậc chịu lửa I, II; loại 2 đối với nhà có bậc chịu lửa III, IV; và loại 3 đối với nhà có bậc chịu lửa V.
# Ngoài những quy định được nói riêng, các cửa của lối ra thoát nạn từ các hành lang tầng đi vào buồng thang bộ phục vụ từ 4 tầng nhà trở lên (ngoại trừ trong các nhà phục vụ mục đích giam giữ, cải tạo) phải bảo đảm:
# a) Tất cả các khóa điện lắp trên cửa phải tự động mở khi hệ thống báo cháy tự động của tòa nhà bị kích hoạt. Ngay khi mất điện thì các khóa điện đó cũng phải tự động mở;
# b) Người sử dụng buồng thang luôn có thể quay trở lại phía trong nhà qua chính cửa vừa đi qua hoặc qua các điểm bố trí cửa quay trở lại phía trong nhà;
# c) Bố trí trước các điểm quay trở lại phía trong nhà theo nguyên tắc các cánh cửa chỉ được phép ngăn cản việc quay trở lại phía trong nhà nếu đáp ứng tất cả các yêu cầu sau:
# - Có không ít hơn hai tầng, nơi có thể đi ra khỏi buồng thang bộ để đến một lối ra thoát nạn khác;
# - Có không quá 4 tầng nằm giữa các tầng nhà có thể đi ra khỏi buồng thang bộ để đến một lối ra thoát nạn khác;
# - Việc quay trở lại phía trong nhà phải có thể thực hiện được tại tầng trên cùng hoặc tầng dưới liền kề với tầng trên cùng được phục vụ bởi buồng thang bộ thoát nạn nếu tầng này cho phép đi đến một lối ra thoát nạn khác;
# - Các cửa cho phép quay trở lại phía trong nhà phải được đánh dấu trên mặt cửa phía trong buồng thang bằng dòng chữ “CỬA CÓ THỂ ĐI VÀO TRONG NHÀ” với chiều cao các chữ ít nhất là 50 mm, chiều cao bố trí không thấp hơn 1,2 m và không cao hơn 1,8 m;
# - Các cửa không cho phép quay trở lại phía trong nhà phải có thông báo trên mặt cửa phía trong buồng thang để nhận biết được vị trí của cửa quay trở lại phía trong nhà hoặc lối ra thoát nạn gần nhất theo từng hướng di chuyển.
# CHÚ THÍCH: 	Đối với các cửa không cho phép quay trở lại phía trong nhà, ở mặt cửa phía hành lang trong nhà (ngoài buồng thang) nên có biển cảnh báo người sử dụng không thể quay trở lại phía trong nhà được khi họ đi qua cửa đó.
# 3.2.12 	Các lối ra không thỏa mãn các yêu cầu đối với lối ra thoát nạn có thể được xem là lối ra khẩn cấp để tăng thêm mức độ an toàn cho người khi có cháy. Mọi lối ra khẩn cấp, bao gồm cả các lối ra khẩn cấp tại 3.2.13, không được đưa vào tính toán thoát nạn khi cháy.
# 3.2.13 	Ngoài trường hợp đã nêu tại 3.2.12, các lối ra khẩn cấp còn gồm có:
# a) Lối ra ban công hoặc lôgia, mà ở đó có khoảng tường đặc với chiều rộng không nhỏ hơn 1,2 m tính từ mép ban công (lôgia) tới ô cửa sổ (hay cửa đi lắp kính) hoặc không nhỏ hơn 1,6 m giữa các ô cửa kính mở ra ban công (lôgia). Ban công hoặc lôgia phải có chiều rộng không nhỏ hơn 0,6 m, bảo đảm có thông gió tự nhiên và được ngăn cách với gian phòng bằng vách ngăn (có các lỗ cửa) từ sàn đến trần. Cho phép thay các khoảng tường đặc nói trên bằng tường kính với giới hạn chịu lửa không thấp hơn EI 30 hoặc EI 15 tùy thuộc vào giới hạn chịu lửa của tường ngoài nhà;
# b) Lối ra dẫn vào một lối đi chuyển tiếp hở (cầu nối) bên ngoài, có chiều rộng không nhỏ hơn 0,6 m, dẫn đến phân khoang cháy liền kề hoặc đến một khoang cháy liền kề. Không cho phép bố trí các kết cấu/cấu kiện bao che cản trở di chuyển của người;
# c) Lối ra ban công hoặc lôgia có chiều rộng không nhỏ hơn 0,6 m, mà ở đó có trang bị thang bên ngoài nối các ban công hoặc lôgia theo từng tầng, hoặc có cửa nắp trên sàn ban công hoặc lôgia, kích thước tối thiểu 0,6 x 0,8 m, có thể thông xuống ban công hoặc lôgia tầng dưới;
# d) Lối ra bên ngoài trực tiếp từ các gian phòng có cao trình sàn hoàn thiện không thấp hơn âm 4,5 m và không cao hơn 5,0 m qua cửa sổ hoặc cửa đi có kích thước không nhỏ hơn 0,75 m × 1,5 m, cũng như qua cửa nắp có kích thước không nhỏ hơn 0,6 m × 0,8 m; khi đó tại các lối ra này phải được trang bị thang leo; độ dốc của các thang leo này không quy định;
# e) Lối ra mái của nhà có bậc chịu lửa I, II và III thuộc cấp S0 và S1 qua cửa sổ, cửa đi hoặc cửa nắp với kích thước và thang leo được quy định như tại đoạn d) của điều này.
# 3.2.14 	Trong các tầng kỹ thuật cho phép bố trí các lối ra thoát nạn với chiều cao không nhỏ hơn 1,8 m.
# Từ các tầng kỹ thuật chỉ dùng để đặt các mạng kỹ thuật công trình (đường ống, đường dây và các đối tượng tương tự) cho phép bố trí lối ra khẩn cấp qua cửa đi với kích thước không nhỏ hơn 0,75 m × 1,5 m hoặc qua cửa nắp với kích thước không nhỏ hơn 0,6 m × 0,8 m mà không cần bố trí lối ra thoát nạn.
# Trong các tầng kỹ thuật hầm các lối ra này phải được ngăn cách với các lối ra khác của nhà và dẫn trực tiếp ra bên ngoài.
# 3.3 	Đường thoát nạn
# 3.3.1 	Các đường thoát nạn phải được chiếu sáng và chỉ dẫn phù hợp với các yêu cầu tại TCVN 3890.
# 3.3.2 	Khoảng cách giới hạn cho phép từ vị trí xa nhất của gian phòng, hoặc từ chỗ làm việc xa nhất tới lối ra thoát nạn gần nhất, được đo theo trục của đường thoát nạn, phải được hạn chế tùy thuộc vào:
# - Nhóm nguy hiểm cháy theo công năng và hạng nguy hiểm cháy nổ (xem Phụ lục C) của gian phòng và nhà;
# - Số lượng người thoát nạn;
# - Các thông số hình học của gian phòng và đường thoát nạn;
# - Cấp nguy hiểm cháy kết cấu và bậc chịu lửa của nhà.
# Chiều dài của đường thoát nạn theo cầu thang bộ loại 2 lấy bằng ba lần chiều cao của thang đó.
# CHÚ THÍCH: 	Các yêu cầu cụ thể về khoảng cách giới hạn cho phép từ vị trí xa nhất đến lối ra thoát nạn gần nhất được nêu trong các quy chuẩn cho từng loại công trình. Một số quy định cụ thể cho các nhóm nhà thường gặp nêu tại Phụ lục G.
# 3.3.3 	Khi bố trí, thiết kế các đường thoát nạn phải căn cứ vào yêu cầu tại 3.2.1. Đường thoát nạn không bao gồm các thang máy, thang cuốn và các đoạn đường được nêu dưới đây:
# - Đường đi qua các hành lang trong có lối ra từ giếng thang máy, qua các sảnh thang máy và các khoang đệm trước thang máy, nếu các kết cấu bao che giếng thang máy, bao gồm cả cửa giếng thang máy, không đáp ứng các yêu cầu như đối với bộ phận ngăn cháy;
# - Đường đi qua các buồng thang bộ khi có lối đi xuyên chiếu tới của buồng thang là một phần của hành lang trong, cũng như đường đi qua gian phòng có đặt cầu thang bộ loại 2, mà cầu thang này không phải là cầu thang để thoát nạn; 
# - Đường đi theo mái nhà, ngoại trừ mái đang được khai thác sử dụng hoặc một phần mái được trang bị riêng cho mục đích thoát nạn;
# - Đường đi theo các cầu thang bộ loại 2, nối thông từ 3 tầng (sàn) trở lên, cũng như dẫn từ tầng hầm và tầng nửa hầm, ngoại trừ các trường hợp cụ thể về thoát nạn theo cầu thang bộ loại 2 nêu tại 3.2.1, 3.2.2, 3.2.6.
# 3.3.4 	Vật liệu hoàn thiện, trang trí tường và trần (bao gồm cả tấm trần treo nếu có), vật liệu ốp lát, vật liệu phủ sàn trên đường thoát nạn tuân thủ yêu cầu tại Bảng B.8, Phụ lục B.
# 3.3.5 	Trong các hành lang trên lối ra thoát nạn nêu tại 3.2.1, ngoại trừ những trường hợp nói riêng trong quy chuẩn, không cho phép bố trí: thiết bị nhô ra khỏi mặt phẳng của tường trên độ cao nhỏ hơn 2 m; các ống dẫn khí cháy và ống dẫn các chất lỏng cháy được, cũng như các tủ tường, trừ các tủ thông tin liên lạc và tủ đặt họng nước chữa cháy.
# Các hành lang, sảnh, phòng chung trên đường thoát nạn phải được bao che bằng các bộ phận ngăn cháy phù hợp quy định trong các quy chuẩn cho từng loại công trình. Bộ phận ngăn cháy bao che đường thoát nạn của nhà có bậc chịu lửa I phải làm bằng vật liệu không cháy với giới hạn chịu lửa ít nhất EI 30, và của nhà có bậc chịu lửa II, III, IV phải làm bằng vật liệu không cháy hoặc cháy yếu (Ch1) với giới hạn chịu lửa ít nhất EI 15. Riêng nhà có bậc chịu lửa II của hạng nguy hiểm cháy và cháy nổ D, E (xem Phụ lục C) có thể bao che hành lang bằng tường kính. Các cửa mở vào hành lang phải là cửa ngăn cháy có giới hạn chịu lửa không thấp hơn giới hạn chịu lửa của bộ phận ngăn cháy.
# Các hành lang dài hơn 60 m phải được phân chia bằng các vách ngăn cháy loại 2 thành các đoạn có chiều dài được xác định theo yêu cầu bảo vệ chống khói nêu tại Phụ lục D, nhưng không được vượt quá 60 m. Các cửa đi trong các vách ngăn cháy này phải phù hợp với các yêu cầu tại 3.2.11.
# Khi các cánh cửa đi của gian phòng mở nhô ra hành lang, thì chiều rộng của đường thoát nạn theo hành lang được lấy bằng chiều rộng thông thủy của hành lang trừ đi:
# - Một nửa chiều rộng phần nhô ra của cánh cửa (tính cho cửa nhô ra nhiều nhất) - khi cửa được bố trí một bên hành lang;
# - Cả chiều rộng phần nhô ra của cánh cửa (tính cho cửa nhô ra nhiều nhất) - khi các cửa được bố trí hai bên hành lang. Yêu cầu này không áp dụng cho hành lang tầng (sảnh chung) nằm giữa cửa ra từ căn hộ và cửa ra dẫn vào buồng thang bộ trong các đơn nguyên nhà nhóm F1.3. 
# 3.3.6 	Chiều cao thông thủy các đoạn nằm ngang của đường thoát nạn không được nhỏ hơn 2 m, chiều rộng thông thủy các đoạn nằm ngang của đường thoát nạn và các đoạn dốc không được nhỏ hơn:
# - 1,2 m - đối với hành lang chung dùng để thoát nạn cho hơn 15 người từ các gian phòng nhóm F1, hơn 50 người - từ các gian phòng thuộc nhóm nguy hiểm cháy theo công năng khác. 
# - 	0,7 m - đối với các lối đi đến các chỗ làm việc đơn lẻ.
# - 1,0 m - trong tất cả các trường hợp còn lại.
# Trong bất kỳ trường hợp nào, các đường thoát nạn phải đủ rộng, có tính đến dạng hình học của chúng, để không cản trở việc vận chuyển các cáng tải thương có người nằm trên. 
# 3.3.7 	Trên sàn của đường thoát nạn không được có các giật cấp với chiều cao chênh lệch nhỏ hơn 45 cm hoặc có gờ nhô lên, ngoại trừ các ngưỡng trong các ô cửa đi. Tại các chỗ có giật cấp phải bố trí bậc thang với số bậc không nhỏ hơn 3 hoặc làm đường dốc với độ dốc không được lớn hơn 1:6 (độ chênh cao không được quá 10 cm trên chiều dài 60 cm hoặc góc tạo bởi đường dốc với mặt bằng không lớn hơn 9,5°). 
# Khi làm bậc thang ở những nơi có chiều cao chênh lệch lớn hơn 45 cm phải bố trí lan can tay vịn.
# Ngoại trừ những trường hợp được quy định riêng tại 3.4.4, trên đường thoát nạn không cho phép bố trí cầu thang xoắn ốc, cầu thang cong toàn phần hoặc từng phần theo mặt bằng và trong phạm vi một bản thang và một buồng thang bộ không cho phép bố trí các bậc có chiều cao khác nhau và chiều rộng mặt bậc khác nhau. Trên đường thoát nạn không được bố trí gương soi gây ra sự nhầm lẫn về đường thoát nạn.
# 3.4 	Cầu thang bộ và buồng thang bộ trên đường thoát nạn
# 3.4.1 	Chiều rộng của bản thang bộ dùng để thoát người, trong đó kể cả bản thang đặt trong buồng thang bộ, không được nhỏ hơn chiều rộng tính toán hoặc chiều rộng của bất kỳ lối ra thoát nạn (cửa đi) nào trên nó, đồng thời không được nhỏ hơn:
# - 1,35 m - đối với nhà nhóm F1.1;
# - 	1,2 m - đối với nhà có số người trên tầng bất kỳ, trừ tầng một, lớn hơn 200 người;
# - 	0,7 m - đối với cầu thang bộ dẫn đến các chỗ làm việc đơn lẻ;
# - 	0,9 m - đối với tất cả các trường hợp còn lại.
# 3.4.2 	Độ dốc (góc nghiêng) của các thang bộ trên các đường thoát nạn không được lớn hơn 1:1 (45°); chiều rộng mặt bậc không được nhỏ hơn 25 cm trừ các cầu thang ngoài nhà, còn chiều cao bậc không được lớn hơn 22 cm và không nhỏ hơn 5 cm.
# Độ dốc (góc nghiêng) của các cầu thang bộ hở đi tới các chỗ làm việc đơn lẻ cho phép tăng đến 2:1 (63,5°).
# Cho phép giảm chiều rộng mặt bậc của cầu thang cong đón tiếp (thường bố trí ở sảnh tầng 1) ở phần thu hẹp tới 22 cm; Cho phép giảm chiều rộng mặt bậc tới 12 cm đối với các cầu thang bộ dẫn tới các tầng kỹ thuật, tầng áp mái, mái nhà không khai thác sử dụng, cũng như chỉ dùng cho các gian phòng có tổng số chỗ làm việc không lớn hơn 5 người (trừ các gian phòng nhóm F5 hạng A hoặc B). 
# Các cầu thang bộ loại 3 phải được làm bằng vật liệu không cháy (trừ đối với nhà có bậc chịu lửa V) và được đặt ở sát các phần đặc (không có ô cửa sổ hay lỗ ánh sáng) của tường có cấp nguy hiểm cháy không thấp hơn K1 và có giới hạn chịu lửa không thấp hơn REI 30 hoặc EI 30 (không quy định giới hạn chịu lửa của phần đặc này của tường đối với nhà có bậc chịu lửa V). Các cầu thang bộ này phải có chiếu thang nằm cùng cao trình với lối ra thoát nạn, có lan can cao 1,2 m và bố trí cách lỗ cửa sổ không nhỏ hơn 1,0 m. Cho phép thay thế các phần đặc của tường bằng tường kính có giới hạn chịu lửa không thấp hơn EI 30. Không quy định giới hạn chịu lửa của các lỗ cửa dẫn từ hành lang ra chiếu tới của thang, cũng như dẫn từ các gian phòng mà cầu thang bộ loại 3 này chỉ sử dụng để thoát nạn cho các gian phòng đó.
# Cầu thang bộ loại 2 phải thỏa mãn các yêu cầu quy định đối với bản thang và chiếu thang trong buồng thang bộ.
# 3.4.3 	Chiều rộng của chiếu thang bộ phải không nhỏ hơn chiều rộng của bản thang. Còn chiều rộng của chiếu thang ở trước lối vào thang máy (chiếu thang đồng thời là sảnh của thang máy) đối với thang máy có cánh cửa bản lề mở ra, phải không nhỏ hơn tổng chiều rộng bản thang và một nửa chiều rộng cánh cửa của thang máy, nhưng không nhỏ hơn 1,6 m.
# Các chiếu nghỉ trung gian trong bản thang bộ thẳng phải có chiều dài không nhỏ hơn 1,0 m.
# Các cửa đi có cánh cửa mở vào buồng thang bộ thì khi mở, cánh cửa không được làm giảm chiều rộng tính toán của các chiếu thang và bản thang.
# 3.4.4 	Trong các nhà thuộc nhóm nguy hiểm cháy theo công năng F4 cho phép bố trí cầu thang cong trên đường thoát nạn khi bảo đảm tất cả những điều kiện sau:
# - Chiều cao của thang không quá 9,0 m;
# - Chiều rộng của vế thang phù hợp với các quy định trong quy chuẩn này;
# - Bán kính cong nhỏ nhất không nhỏ hơn 2 lần chiều rộng vế thang;
# - Chiều cao cổ bậc nằm trong khoảng từ 150 mm đến 190 mm;
# - Chiều rộng phía trong của mặt bậc (đo cách đầu nhỏ nhất của bậc 270 mm) không nhỏ hơn 220 mm;
# - Chiều rộng đo tại giữa chiều dài của mặt bậc không nhỏ hơn 250 mm;
# - Chiều rộng phía ngoài của mặt bậc (đo cách đầu to nhất của bậc 270 mm) không quá 450 mm;
# - Tổng của 2 lần chiều cao cổ bậc với chiều rộng phía trong mặt bậc không nhỏ hơn 480 mm và với chiều rộng phía ngoài của mặt bậc không lớn hơn 800 mm.
# 3.4.5 	Trong các buồng thang bộ và khoang đệm (nếu có) không cho phép bố trí:
# - Các ống dẫn khí cháy và chất lỏng cháy được;
# - Các tủ tường, trừ các tủ thông tin liên lạc và tủ chứa các họng nước chữa cháy;
# - Các cáp và dây điện đi hở (trừ dây điện cho thiết bị điện dòng thấp và dây điện cho chiếu sáng hành lang và buồng thang bộ);
# - Các lối ra từ thang tải và thiết bị nâng hàng; 
# - Các lối ra gian phòng kho hoặc phòng kỹ thuật;
# - Các thiết bị nhô ra khỏi mặt tường ở độ cao dưới 2,2 m tính từ bề mặt của các bậc và chiếu thang.
# Trong không gian của các buồng thang bộ thoát nạn và khoang đệm ngăn cháy có áp suất không khí dương khi có cháy, không cho phép bố trí bất kỳ phòng công năng nào.
# 3.4.6 	Trong không gian của các buồng thang bộ, trừ các buồng thang không nhiễm khói, cho phép bố trí không quá hai thang máy chở người hạ xuống chỉ đến tầng 1 với các kết cấu bao che giếng thang làm từ các vật liệu không cháy.
# Các giếng thang máy nằm ngoài nhà, nếu cần bao che thì phải sử dụng các kết cấu làm từ vật liệu không cháy.
# 3.4.7 	Các buồng thang bộ, trừ các trường hợp được quy định riêng trong quy chuẩn này, phải có lối ra ngoài trực tiếp tới khu đất liền kề nhà hoặc qua tiền sảnh được ngăn cách với các hành lang và các gian phòng tiếp giáp bằng các vách ngăn cháy loại 1 có cửa đi với cơ cấu tự đóng và khe cửa phải được chèn kín. 
# Khi bố trí các lối ra thoát nạn từ hai buồng thang bộ trở lên qua tiền sảnh chung thì các buồng thang bộ (trừ một trong số đó) phải có cửa ra bên ngoài trực tiếp trừ lối ra dẫn vào sảnh. Trong trường hợp chỉ có một buồng thang bộ dẫn vào tiền sảnh thì buồng thang bộ này phải có lối ra ngoài trực tiếp.
# Cho phép bố trí các lối ra thoát nạn từ hai buồng thang bộ qua tiền sảnh chung đối với các nhà có chiều cao PCCC dưới 28 m, diện tích mỗi tầng không quá 300 m2, có số người sử dụng ở mỗi tầng tính lớn nhất theo thiết kế được duyệt, khi thiết kế không chỉ rõ giá trị này, số lượng người lớn nhất được tính bằng tỷ số giữa diện tích sàn của phòng, của tầng hoặc của nhà chia cho hệ số không gian sàn (m2/người) quy định tại Bảng G.9 không vượt quá 50 người và toàn bộ nhà được bảo vệ hệ thống chữa cháy tự động phù hợp với quy định hiện hành.
# Đối với các nhà ga hành khách và các sảnh rộng lớn có đặc điểm sử dụng tương tự, có thể coi là lối ra thoát nạn đối với các lối ra từ 50% số buồng thang bộ (hoặc từ các hành lang) vào sảnh hành khách chung có lối thoát nạn trực tiếp ra ngoài, ra cầu vượt hở bên ngoài, hoặc ra sân ga. 
# Các buồng thang bộ loại N1 phải có lối ra ngoài trực tiếp.
# 3.4.8 	Các buồng thang bộ phải được bảo đảm chiếu sáng tự nhiên hoặc nhân tạo.
# a) Trường hợp chiếu sáng tự nhiên:
# Trừ buồng thang bộ loại L2, việc bảo đảm chiếu sáng có thể được thực hiện bằng các lỗ lấy ánh sáng với diện tích không nhỏ hơn 1,2 m2 trên các tường ngoài ở mỗi tầng. 
# Các buồng thang bộ loại L2 phải có lỗ lấy ánh sáng trên mái có diện tích không nhỏ hơn 4 m2 với khoảng hở giữa các vế thang có chiều rộng không nhỏ hơn 0,7 m hoặc giếng lấy sáng theo suốt chiều cao của buồng thang bộ với diện tích mặt cắt ngang không nhỏ hơn 2 m2.
# Cho phép bố trí không quá 50% buồng thang bộ bên trong không có các lỗ lấy ánh sáng, dùng để thoát nạn, trong các trường hợp sau:
# - Các nhà thuộc nhóm F2, F3 và F4: đối với buồng thang loại N2 hoặc N3 có áp suất không khí dương khi cháy;
# - Các nhà thuộc nhóm F5 hạng C có chiều cao PCCC tới 28 m, còn hạng D và E không phụ thuộc chiều cao PCCC của nhà: đối với buồng thang loại N3 có áp suất không khí dương khi cháy.
# b) Trường hợp chiếu sáng nhân tạo:
# Trường hợp không bố trí được các lỗ cửa như quy định tại đoạn a) của 3.4.8 thì các buồng thang bộ thoát nạn phải là buồng thang bộ không nhiễm khói và được trang bị chiếu sáng nhân tạo, được cấp điện như chú thích tại 3.4.13 bảo đảm nguyên tắc duy trì liên tục nguồn điện cấp cho hệ thống chiếu sáng hoạt động ổn định khi có cháy xảy ra, và ánh sáng phải đủ để người thoát nạn theo các buồng thang này có thể nhìn rõ đường thoát nạn và không bị lóa mắt.
# 3.4.9 	Việc bảo vệ chống khói các buồng thang bộ loại N2 và N3 phải tuân theo Phụ lục D. Khi cần thiết, các buồng thang bộ loại N2 phải được chia thành các khoang theo chiều cao bằng các vách ngăn cháy đặc loại 1 với lối đi lại giữa các khoang nằm ngoài không gian buồng thang bộ.
# Các cửa sổ trong các buồng thang bộ loại N2 phải là cửa sổ không mở được.
# Khoang đệm của các buồng thang bộ loại N3 phải có diện tích không nhỏ hơn 3,0 m2 và không nhỏ hơn 6,0 m2 nếu khoang đệm đó đồng thời là sảnh của thang máy chữa cháy.
# 3.4.10 	Tính không nhiễm khói của khoảng đệm không nhiễm khói dẫn tới các buồng thang bộ không nhiễm khói loại N1 phải được bảo đảm bằng thông gió tự nhiên với các giải pháp kết cấu và bố trí mặt bằng - không gian phù hợp. Một số trường hợp được cho là phù hợp như sau:
# CHÚ THÍCH: 	Một số phương án bố trí khoảng đệm không nhiễm khói dẫn vào buồng thang bộ loại N1 được minh họa tại I.3.2 (Phụ lục I).
# a) Các khoảng đệm không nhiễm khói phải để hở, thông với bên ngoài, thường đặt tại các góc bên trong của nhà, đồng thời phải bảo đảm các yêu cầu sau (xem Hình I.7):
# - Khi một phần của tường ngoài của nhà nối tiếp với phần tường khác dưới một góc nhỏ hơn 135o thì khoảng cách theo phương ngang từ lỗ cửa đi gần nhất ở khoảng đệm này tới đỉnh góc tiếp giáp phải không nhỏ hơn 4 m; khoảng cách này có thể giảm đến bằng giá trị phần nhô ra của tường ngoài. Yêu cầu này không áp dụng đối với lối đi, nằm ở các góc tiếp giáp lớn hơn hoặc bằng 135o, cũng như cho phần nhô ra của tường ngoài có giá trị không lớn hơn 1,2 m;
# - Chiều rộng phần tường giữa các lỗ cửa đi của khoảng đệm không nhiễm khói và ô cửa sổ gần nhất của gian phòng không được nhỏ hơn 2 m;
# - Các lối đi phải có chiều rộng không nhỏ hơn 1,2 m với chiều cao lan can 1,2 m, chiều rộng của phần tường giữa các lỗ cửa đi ở khoảng đệm không nhiễm khói phải không nhỏ hơn 1,2 m.
# CHÚ THÍCH: 	Một số trường hợp tương tự dạng này được minh họa trong Phụ lục I, Hình I.8 a), b) và c).
# b) Khoảng đệm không nhiễm khói đi theo hành lang bên (xem Hình I.8 h), i) và k)) được chiếu sáng và thông gió tự nhiên bằng các lỗ thông mở ra phía và tiếp xúc với một trong những không gian sau:
# - Không gian bên ngoài; 
# - Một đường phố hoặc đường công cộng hoặc các không gian công cộng khác thông hoàn toàn ở phía trên;
# - Một giếng thông gió thẳng đứng có chiều rộng không nhỏ hơn 6 m và diện tích mặt thoáng không nhỏ hơn 93 m2;
# c) Khoảng đệm không nhiễm khói đi qua một sảnh ngăn khói có diện tích không nhỏ hơn 6 m2 với kích thước nhỏ nhất theo mỗi chiều không nhỏ hơn 2 m được ngăn cách với các khu vực liền kề của tòa nhà bằng tường ngăn cháy loại 2. Các cửa ra vào phải có cơ cấu tự đóng và khe cửa phải được chèn kín. Thiết kế của sảnh ngăn khói phải bảo đảm không cản trở sự di chuyển của người sử dụng trên đường thoát nạn. Tính không nhiễm khói của sảnh ngăn khói phải được bảo đảm bởi một trong những giải pháp sau:
# - Có các lỗ thông gió với diện tích không nhỏ hơn 15% diện tích sàn của sảnh ngăn khói và đặt cách không quá 9 m tính từ bất kỳ bộ phận nào của sảnh. Các lỗ thông gió này phải thông với một giếng đứng hoặc khoang lõm thông khí trên suốt dọc chiều cao nhà. Kích thước của giếng đứng hoặc khoang lõm phải bảo đảm chiều rộng không nhỏ hơn 6 m và diện tích mặt thoáng không nhỏ hơn 93 m2. Tường bao giếng đứng phải có khả năng chịu lửa nhỏ nhất là 1 giờ và trong giếng không được có lỗ thông nào khác ngoài các lỗ thông gió của sảnh ngăn khói, buồng thang thoát nạn và các khu vệ sinh (xem Hình I.8 d), e), f));
# - Là hành lang được thông gió ngang, có các lỗ thông gió cố định nằm ở hai tường bên ngoài. Các lỗ thông trên mỗi bức tường ngoài không được nhỏ hơn 50% diện tích mặt thoáng của tường ngoài đối diện. Khoảng cách từ mọi điểm của sàn hành lang đến một lỗ thông bất kỳ không được lớn hơn 13 m (xem Hình I.8 g)).
# 3.4.11 	Các buồng thang bộ loại L1 và cầu thang bộ loại 3 được phép bố trí trong các nhà thuộc tất cả các nhóm nguy hiểm cháy theo công năng có chiều cao PCCC tới 28 m; khi đó, trong nhà nhóm F5 hạng A hoặc B, lối ra hành lang tầng từ các gian phòng hạng A hoặc B phải đi qua khoang đệm luôn luôn có áp suất không khí dương.
# 3.4.12 	Các buồng thang bộ loại L2 được phép bố trí trong các nhà có bậc chịu lửa I, II, III thuộc cấp nguy hiểm cháy kết cấu S0, S1 và nhóm nguy hiểm cháy theo công năng F1, F2, F3 và F4, với chiều cao PCCC không quá 9 m. Cho phép tăng chiều cao này đến 12 m (trừ các nhà cơ sở y tế nội trú) với điều kiện lỗ mở lấy sáng trên cao được mở tự động khi có cháy. Số lượng các buồng thang như vậy (trừ các nhà nhóm F1.3 và F1.4) cho phép tối đa 50%, các buồng thang bộ còn lại phải có lỗ lấy sáng trên tường ngoài tại mỗi tầng. 
# Khi bố trí các buồng thang bộ loại L2, còn phải bảo đảm yêu cầu sau: Đối với các nhà nhóm F1.3 dạng đơn nguyên, trong từng căn hộ có bố trí ở độ cao trên 4 m phải có một lối ra khẩn cấp theo quy định tại 3.2.13.
# 3.4.13 	Trong các nhà có chiều cao PCCC lớn hơn 28 m (trừ các nhà nhóm F5 hạng C, E không có người làm việc thường xuyên), cũng như trong các nhà nhóm F5 hạng A hoặc B phải bố trí buồng thang bộ không nhiễm khói, trong đó phải bố trí buồng thang loại N1.
# Trong các nhà có nhiều công năng, các buồng thang bộ nối giữa các phần nhà có nhóm nguy hiểm cháy theo công năng khác nhau phải là buồng thang bộ không nhiễm khói phù hợp với các yêu cầu của điều này, trừ các trường hợp được quy định riêng.
# CHÚ THÍCH: 	Buồng thang bộ N1 có thể được thay thế như đã nêu tại 2.5.1c) của với điều kiện hệ thống cung cấp không khí bên ngoài vào khoang đệm và vào buồng thang phải được cấp điện ưu tiên từ hai nguồn độc lập (1 nguồn điện lưới và 1 nguồn máy phát điện dự phòng) bảo đảm nguyên tắc duy trì liên tục nguồn điện cấp cho hệ thống hoạt động ổn định khi có cháy xảy ra.
# Cho phép:
# a) Trong các nhà nhóm F1, F2, F3, F4 bố trí không quá 50% buồng thang bộ loại N3 hoặc loại N2 có lối vào buồng thang đi qua khoang đệm với giải pháp bao che giống như khoang đệm ngăn cháy loại 1 (nghĩa là không yêu cầu có áp suất không khí dương trong khoang đệm này, nhưng các bộ phận bao che phải có giới hạn chịu lửa tương tự như khoang đệm ngăn cháy loại 1);
# b) Khi nhà có từ hai tầng hầm trở lên, việc thoát nạn từ các tầng hầm này có thể theo các buồng thang bộ loại N3, hoặc loại N2 có lối vào buồng thang đi qua khoang đệm với giải pháp bao che giống như khoang đệm ngăn cháy loại 1;
# c) Trong các nhà nhóm F5 bố trí các buồng thang bộ không nhiễm khói thay cho loại N1 như sau:
# - Trong các nhà hạng A hoặc B - các buồng thang bộ N2 hoặc N3 có áp suất không khí dương thường xuyên;
# - Trong các nhà hạng C - các buồng thang bộ N2 hoặc N3 với áp suất không khí dương khi có cháy;
# - Trong các nhà hạng D, E - các buồng thang bộ N2 hoặc N3 với áp suất không khí dương khi có cháy, hoặc các buồng thang bộ L1 với điều kiện buồng thang phải được phân khoang bằng vách ngăn cháy đặc qua mỗi 20 m chiều cao và lối đi từ khoang này sang khoang khác của buồng thang phải đặt ở ngoài không gian của buồng thang.
# 3.4.14 	Trong các nhà có các buồng thang bộ không nhiễm khói phải bố trí bảo vệ chống khói cho các hành lang chung, các sảnh, các không gian chung và các phòng chờ.
# 3.4.15 	Trong các nhà có bậc chịu lửa I và II; và cấp nguy hiểm cháy kết cấu S0, cho phép bố trí các cầu thang bộ loại 2 đi từ tiền sảnh lên tầng hai có tính đến các yêu cầu tại 4.26.
# Trong các nhà nhóm F3.1 và F3.2 cho phép sử dụng cầu thang nói trên kể cả khi không có tiền sảnh.
# 3.4.16 	Trong các nhà có chiều cao PCCC không quá 28 m thuộc các nhóm nguy hiểm cháy theo công năng F1.2, F2, F3, F4, với bậc chịu lửa I, II và cấp nguy hiểm cháy kết cấu S0, thì cho phép sử dụng các cầu thang bộ loại 2 nối hai tầng trở lên, khi các buồng thang bộ thoát nạn đáp ứng yêu cầu của các tài liệu chuẩn và quy định tại 4.27. Các cầu thang bộ loại 2 nối thông từ 3 tầng (sàn) trở lên không được tính toán, sử dụng làm đường thoát nạn khi có cháy, trừ các trường hợp quy định tại 3.2.1, 3.2.2, 3.2.6.
# 3.4.17 	Các thang cuốn phải được bố trí phù hợp các yêu cầu quy định cho cầu thang bộ loại 2.
# 3.5 	Yêu cầu về an toàn cháy đối với các vật liệu xây dựng cho nhà
# 3.5.1 	Vật liệu xây dựng được sử dụng cho nhà phụ thuộc vào công dụng và tính nguy hiểm cháy của vật liệu.
# 3.5.2 	Các yêu cầu về an toàn cháy đối với việc áp dụng các vật liệu xây dựng trong nhà được quy định tương ứng với các chỉ tiêu về tính nguy hiểm cháy của vật liệu quy định tại Bảng B.7 (Phụ lục B).
# 3.5.3 		Việc sử dụng các vật liệu hoàn thiện - trang trí, vật liệu ốp lát và vật liệu phủ sàn trên các đường thoát nạn phải tuân thủ yêu cầu tại 3.3.4, còn đối với các phòng sử dụng chung (trừ vật liệu phủ sàn của các sàn thi đấu thể thao và các sàn của phòng nhảy) - tuân thủ quy định tại Bảng B.9 (Phụ lục B).
# 3.5.4 Trong các gian phòng của nhà thuộc nhóm F5, hạng A, B và C1 có sử dụng hoặc bảo quản các chất lỏng dễ cháy, vật liệu phủ sàn phải có cấp nguy hiểm cháy vật liệu không nguy hiểm hơn CV1.
# 3.5.5 Trong các gian gửi đồ của nhà nhóm F2.1, không cho phép sử dụng: các loại vật liệu hoàn thiện tường, trần và trần treo, vật liệu ốp lát có cấp nguy hiểm cháy vật liệu nguy hiểm hơn CV1; vật liệu phủ sàn có cấp nguy hiểm cháy vật liệu nguy hiểm hơn CV2.
# 3.5.6 Trong các gian phòng lưu trữ sách, hồ sơ, tài liệu và các vật phẩm tương tự, chỉ được sử dụng vật liệu hoàn thiện, trang trí, vật liệu ốp lát và vật liệu phủ sàn có cấp nguy hiểm cháy CV0 hoặc CV1. 
# 3.5.7 Trong các gian trưng bày của bảo tàng, triển lãm và các gian phòng có tính chất tương tự thuộc nhóm F2.2, không cho phép sử dụng các vật liệu hoàn thiện tường, trần và trần treo có cấp nguy hiểm cháy cao hơn CV2, vật liệu phủ sàn có cấp nguy hiểm cháy vật liệu nguy hiểm hơn CV3.
# 3.5.8 Trong các gian phòng thương mại của nhà nhóm F3.1, không cho phép sử dụng các vật liệu hoàn thiện tường, trần, trần treo có cấp nguy hiểm cháy vật liệu nguy hiểm hơn CV2, vật liệu phủ sàn có cấp nguy hiểm cháy vật liệu nguy hiểm hơn CV3.
# 3.5.9 Trong các gian phòng chờ của nhà nhóm F3.3, vật liệu hoàn thiện tường, trần, trần treo và vật liệu phủ sàn phải có cấp nguy hiểm cháy CV0.
# 3.5.10 Cho phép áp dụng các yêu cầu về an toàn cháy đối với vật liệu hoàn thiện - trang trí, vật liệu ốp lát, vật liệu phủ sàn và các tiêu chí thử nghiệm tương ứng theo các tài liệu chuẩn được phép áp dụng để thay thế cho các yêu cầu từ 3.5.1 đến 3.5.9 và Phụ lục B, trừ các yêu cầu quy định tại A.4. 
# ''')
# 
# asyncio.run(main())

