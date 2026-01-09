"""질병 정보 시드 데이터 스크립트

일반적인 증상과 질병 정보를 데이터베이스에 저장합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.embedding import get_embedding_service

# 샘플 질병 데이터 (국가건강정보포털 기반)
SAMPLE_DISEASES = [
    {
        "id": "D001",
        "name": "감기 (급성 상기도 감염)",
        "name_en": "Common Cold",
        "category": "호흡기 질환",
        "description": "감기는 바이러스에 의해 발생하는 급성 상기도 감염입니다. 코, 인후, 후두, 기관지 등 상기도를 침범하며, 가장 흔한 급성 질환 중 하나입니다.",
        "causes": "라이노바이러스, 코로나바이러스, 아데노바이러스 등 200여 가지 이상의 바이러스가 원인입니다. 감염자의 비말이나 손을 통해 전파됩니다. 면역력이 저하되거나, 과로, 스트레스, 영양 불균형 시 발병 위험이 높아집니다.",
        "symptoms": "콧물, 코막힘, 재채기, 인후통(목 아픔), 기침, 가래, 미열, 두통, 근육통, 전신 피로감. 증상은 보통 1-2주 내에 호전됩니다.",
        "diagnosis": "대부분 증상만으로 진단합니다. 특별한 검사가 필요하지 않으며, 증상이 심하거나 오래 지속되면 추가 검사를 시행할 수 있습니다.",
        "treatment": "충분한 휴식과 수분 섭취가 기본입니다. 해열진통제로 열과 통증을 조절하고, 코막힘에는 비충혈제거제, 기침에는 진해제를 사용할 수 있습니다. 항생제는 세균 감염이 동반된 경우에만 사용합니다.",
        "prevention": "손 씻기를 철저히 하고, 감염자와 접촉을 피합니다. 충분한 수면과 균형 잡힌 식사로 면역력을 유지합니다.",
        "related_drugs": "타이레놀, 판콜에이, 화이투벤, 콘택600, 지르텍"
    },
    {
        "id": "D002",
        "name": "두통",
        "name_en": "Headache",
        "category": "신경계 질환",
        "description": "두통은 머리 부위에 통증이 발생하는 것으로, 가장 흔한 증상 중 하나입니다. 긴장형 두통, 편두통, 군발성 두통 등 여러 종류가 있습니다.",
        "causes": "긴장형 두통은 스트레스, 피로, 자세 불량으로 발생합니다. 편두통은 뇌혈관 확장, 세로토닌 변화, 유전적 요인과 관련됩니다. 이차성 두통은 감염, 뇌종양, 뇌출혈 등 다른 질환에 의해 발생합니다.",
        "symptoms": "긴장형: 양측 조이는 듯한 통증. 편두통: 한쪽 박동성 통증, 구역, 빛/소리 민감. 군발성: 한쪽 눈 주위 극심한 통증, 눈물, 코막힘. 위험 신호: 갑자기 시작된 극심한 두통, 발열 동반, 의식 변화.",
        "diagnosis": "병력 청취와 신경학적 검사가 기본입니다. 이차성 두통이 의심되면 CT, MRI, 뇌척수액 검사 등을 시행합니다.",
        "treatment": "긴장형 두통에는 진통제(아세트아미노펜, 이부프로펜)가 효과적입니다. 편두통에는 트립탄 계열 약물을 사용합니다. 만성 두통의 경우 예방 치료가 필요할 수 있습니다.",
        "prevention": "규칙적인 수면, 스트레스 관리, 카페인/알코올 조절, 규칙적인 운동이 도움됩니다. 두통 유발 요인을 파악하고 피하는 것이 중요합니다.",
        "related_drugs": "게보린, 타이레놀, 이부프로펜, 펜잘, 탁센"
    },
    {
        "id": "D003",
        "name": "소화불량 (기능성 소화불량)",
        "name_en": "Dyspepsia",
        "category": "소화기 질환",
        "description": "소화불량은 상복부 불쾌감, 통증, 팽만감, 조기 포만감 등을 특징으로 하는 증상입니다. 기질적 원인 없이 발생하는 기능성 소화불량이 가장 흔합니다.",
        "causes": "위장 운동 장애, 위 배출 지연, 내장 과민성, 헬리코박터 파일로리 감염, 스트레스와 불안, 불규칙한 식습관, 과식, 기름진 음식 등이 원인입니다.",
        "symptoms": "식후 상복부 불쾌감, 더부룩함, 포만감, 속쓰림, 구역, 트림, 식욕 감소. 심한 경우 체중 감소가 동반될 수 있습니다.",
        "diagnosis": "증상과 병력을 확인합니다. 위내시경으로 위암, 위궤양 등 기질적 질환을 배제합니다. 헬리코박터 검사를 시행할 수 있습니다.",
        "treatment": "식습관 개선이 기본입니다. 위장운동촉진제(돔페리돈, 모사프리드), 위산분비억제제(PPI, H2차단제), 소화효소제를 사용합니다. 헬리코박터 양성시 제균 치료를 합니다.",
        "prevention": "규칙적인 식사, 천천히 씹어 먹기, 과식 피하기, 기름진 음식 제한, 스트레스 관리, 금연, 적절한 운동이 도움됩니다.",
        "related_drugs": "베아제, 훼스탈, 가스터, 게비스콘, 알마겔"
    },
    {
        "id": "D004",
        "name": "고혈압",
        "name_en": "Hypertension",
        "category": "순환기 질환",
        "description": "고혈압은 혈압이 지속적으로 높은 상태(수축기 140mmHg 이상 또는 이완기 90mmHg 이상)를 말합니다. 심혈관 질환의 주요 위험 요인입니다.",
        "causes": "90-95%는 원인 불명의 본태성 고혈압입니다. 유전적 요인, 과도한 염분 섭취, 비만, 음주, 흡연, 스트레스, 운동 부족이 위험 요인입니다. 5-10%는 신장 질환, 내분비 질환 등에 의한 이차성 고혈압입니다.",
        "symptoms": "대부분 무증상입니다. 간혹 두통, 어지러움, 코피, 피로감이 나타날 수 있습니다. 고혈압성 위기 시 심한 두통, 시력 장애, 흉통, 호흡 곤란이 발생합니다.",
        "diagnosis": "정확한 혈압 측정이 중요합니다. 여러 번 측정하여 평균을 확인하고, 24시간 활동 혈압 측정을 하기도 합니다. 합병증 평가를 위해 심전도, 심초음파, 신장 기능 검사 등을 시행합니다.",
        "treatment": "생활습관 개선이 기본입니다. 필요시 혈압강하제(ACE억제제, ARB, 칼슘채널차단제, 이뇨제, 베타차단제)를 복용합니다. 대부분 평생 약물 치료가 필요합니다.",
        "prevention": "저염식(하루 6g 미만), 건강한 체중 유지, 규칙적인 운동(주 5일, 30분 이상), 금연, 절주, 스트레스 관리가 중요합니다.",
        "related_drugs": "아모디핀, 로사르탄, 리시노프릴, 히드로클로로티아지드"
    },
    {
        "id": "D005",
        "name": "당뇨병",
        "name_en": "Diabetes Mellitus",
        "category": "내분비 질환",
        "description": "당뇨병은 인슐린 분비 또는 작용의 결함으로 혈당이 지속적으로 높은 만성 대사 질환입니다. 제1형, 제2형, 임신성 당뇨로 분류됩니다.",
        "causes": "제1형은 자가면역에 의한 췌장 베타세포 파괴입니다. 제2형은 인슐린 저항성과 분비 장애로 발생하며, 비만, 가족력, 운동 부족, 불건강한 식습관이 위험 요인입니다.",
        "symptoms": "다뇨(소변량 증가), 다음(갈증), 다식(식욕 증가), 체중 감소, 피로감, 시력 저하, 상처 회복 지연, 잦은 감염. 무증상인 경우도 많습니다.",
        "diagnosis": "공복 혈당 126mg/dL 이상, 당화혈색소(HbA1c) 6.5% 이상, 75g 경구당부하검사 2시간 후 혈당 200mg/dL 이상 중 하나를 만족하면 진단합니다.",
        "treatment": "제1형은 인슐린 주사가 필수입니다. 제2형은 생활습관 개선과 함께 경구혈당강하제(메트포르민, 설포닐우레아 등)를 사용하며, 필요시 인슐린을 추가합니다. 혈당, 혈압, 지질 관리를 함께 합니다.",
        "prevention": "건강한 체중 유지, 규칙적인 운동, 균형 잡힌 식사, 정기적인 건강검진으로 조기 발견이 중요합니다. 당뇨 전단계에서 생활습관 개선으로 당뇨병 발생을 예방할 수 있습니다.",
        "related_drugs": "메트포르민, 글리메피리드, 자뉘비아, 트루리시티, 인슐린"
    },
    {
        "id": "D006",
        "name": "위염",
        "name_en": "Gastritis",
        "category": "소화기 질환",
        "description": "위염은 위 점막에 염증이 생긴 상태로, 급성 위염과 만성 위염으로 구분됩니다. 매우 흔한 질환으로 대부분 치료 가능합니다.",
        "causes": "헬리코박터 파일로리 감염이 가장 흔한 원인입니다. 진통제(NSAIDs), 아스피린 등 약물, 과도한 음주, 스트레스, 흡연, 자극적인 음식도 원인입니다.",
        "symptoms": "상복부 통증, 속쓰림, 더부룩함, 구역, 구토, 소화불량, 식욕 감소. 출혈성 위염의 경우 검은 변(흑변)이나 토혈이 발생할 수 있습니다.",
        "diagnosis": "증상과 병력 확인이 기본입니다. 위내시경으로 위 점막 상태를 직접 확인하고 조직검사를 할 수 있습니다. 헬리코박터 검사(요소호기검사, 대변항원검사, 혈청검사)를 시행합니다.",
        "treatment": "원인 제거가 중요합니다. 위산분비억제제(PPI), 위점막보호제를 사용합니다. 헬리코박터 양성시 항생제 병합 제균 치료를 합니다. 급성기에는 금식하고 정맥 수액 치료를 하기도 합니다.",
        "prevention": "규칙적인 식사, 자극적인 음식 피하기, 금주, 금연, 스트레스 관리. NSAIDs 장기 복용 시 위장보호제 병용을 고려합니다.",
        "related_drugs": "넥시움, 오메프라졸, 란소프라졸, 가스터, 게비스콘"
    },
    {
        "id": "D007",
        "name": "변비",
        "name_en": "Constipation",
        "category": "소화기 질환",
        "description": "변비는 배변 횟수 감소(주 3회 미만), 단단한 변, 배변 시 과도한 힘주기, 불완전 배변감 등을 특징으로 합니다. 매우 흔한 증상입니다.",
        "causes": "섬유소 부족, 수분 섭취 부족, 운동 부족이 가장 흔합니다. 약물(진통제, 항우울제, 철분제 등), 갑상선기능저하증, 당뇨병 등 전신 질환, 대장암 등 기질적 질환도 원인입니다.",
        "symptoms": "배변 횟수 감소, 단단한 변, 배변 시 힘주기, 배변 후 잔변감, 복부 팽만감, 복통. 장기간 지속되면 치질, 치열 등 합병증이 발생할 수 있습니다.",
        "diagnosis": "병력과 증상 확인이 기본입니다. 경고 증상(체중 감소, 혈변, 빈혈 등)이 있으면 대장내시경을 시행합니다. 필요시 대장통과시간 검사, 배변조영술 등을 합니다.",
        "treatment": "생활습관 개선이 가장 중요합니다. 필요시 팽창성 완하제(차전자피), 삼투성 완하제(락툴로오스, 마그네슘), 자극성 완하제(비사코딜)를 사용합니다. 만성 변비에는 장운동촉진제를 사용하기도 합니다.",
        "prevention": "고섬유소 식이(채소, 과일, 통곡물), 충분한 수분 섭취(하루 1.5-2L), 규칙적인 운동, 규칙적인 배변 습관, 변의를 참지 않는 것이 중요합니다.",
        "related_drugs": "둘코락스, 마그밀, 아락실, 포타락스, 락툴로스"
    },
    {
        "id": "D008",
        "name": "알레르기 비염",
        "name_en": "Allergic Rhinitis",
        "category": "알레르기 질환",
        "description": "알레르기 비염은 특정 알레르겐에 대한 과민 반응으로 코 점막에 염증이 생기는 질환입니다. 계절성과 통년성으로 구분됩니다.",
        "causes": "집먼지진드기, 꽃가루, 곰팡이, 동물 털/비듬, 바퀴벌레 등이 원인 알레르겐입니다. 유전적 소인이 있으며, 대기오염, 흡연 등 환경 요인도 영향을 줍니다.",
        "symptoms": "수양성 콧물, 재채기, 코막힘, 코 가려움. 눈 가려움, 충혈, 눈물(알레르기 결막염)이 동반되기도 합니다. 두통, 후각 감소, 수면 장애가 생길 수 있습니다.",
        "diagnosis": "증상과 병력 확인이 기본입니다. 피부반응검사(피부단자검사)로 원인 알레르겐을 확인합니다. 혈액검사로 알레르겐 특이 IgE를 측정할 수 있습니다.",
        "treatment": "원인 알레르겐 회피가 중요합니다. 항히스타민제(경구, 비강 스프레이), 비강 스테로이드 스프레이, 류코트리엔 조절제를 사용합니다. 심한 경우 면역요법(탈감작 치료)을 고려합니다.",
        "prevention": "원인 알레르겐 노출 최소화가 핵심입니다. 집먼지진드기 방지 침구 사용, 정기적인 청소, 꽃가루 시즌에는 외출 자제, 마스크 착용 등이 도움됩니다.",
        "related_drugs": "지르텍, 클라리틴, 아바미스, 나조넥스, 씽귤레어"
    },
    {
        "id": "D009",
        "name": "요통 (허리 통증)",
        "name_en": "Low Back Pain",
        "category": "근골격계 질환",
        "description": "요통은 허리 부위의 통증으로, 성인의 80% 이상이 일생에 한 번 이상 경험합니다. 급성과 만성으로 구분되며, 대부분 양성 경과를 보입니다.",
        "causes": "근육/인대 염좌가 가장 흔합니다. 추간판 탈출증(디스크), 척추관 협착증, 퇴행성 변화, 골다공증, 척추 골절 등도 원인입니다. 자세 불량, 무거운 것 들기, 비만도 관련됩니다.",
        "symptoms": "허리 통증이 주 증상입니다. 디스크의 경우 다리로 뻗치는 방사통이 특징적입니다. 근력 약화, 감각 이상, 배뇨/배변 장애(마미총 증후군)는 응급 상황입니다.",
        "diagnosis": "병력과 신경학적 검사가 기본입니다. 경고 증상이 없으면 영상 검사 없이 보존적 치료를 먼저 합니다. 필요시 X선, MRI를 시행합니다.",
        "treatment": "급성기에는 휴식과 진통제(아세트아미노펜, NSAIDs)를 사용합니다. 근육이완제, 물리치료, 운동 치료가 도움됩니다. 심한 경우 신경차단술, 수술을 고려합니다.",
        "prevention": "올바른 자세, 적절한 체중 유지, 규칙적인 운동(코어 근육 강화), 무거운 것 들 때 허리가 아닌 무릎 사용, 오래 앉아있지 않기가 중요합니다.",
        "related_drugs": "케토톱, 에어탈, 낙센, 근육이완제, 타이레놀"
    },
    {
        "id": "D010",
        "name": "불면증",
        "name_en": "Insomnia",
        "category": "수면 장애",
        "description": "불면증은 잠들기 어렵거나, 자주 깨거나, 새벽에 일찍 깨어 다시 잠들지 못하는 상태입니다. 주간 기능 저하를 동반할 때 진단합니다.",
        "causes": "스트레스, 불안, 우울증이 가장 흔합니다. 불규칙한 수면 습관, 카페인/알코올, 약물(스테로이드, 이뇨제 등), 수면무호흡증, 하지불안증후군도 원인입니다.",
        "symptoms": "잠들기 어려움, 자주 깸, 새벽 조기 각성, 수면 후 개운치 않음. 주간에 피로, 집중력 저하, 기억력 감소, 짜증, 업무/학업 능력 저하가 동반됩니다.",
        "diagnosis": "병력 청취가 중요합니다. 수면 일기를 작성하게 합니다. 다른 수면 질환 감별을 위해 수면다원검사가 필요할 수 있습니다. 우울증, 불안장애 등 동반 질환을 확인합니다.",
        "treatment": "수면 위생 교육이 기본입니다. 인지행동치료가 가장 효과적입니다. 필요시 수면제(졸피뎀, 트라조돈 등)를 단기간 사용합니다. 동반 질환(우울증, 불안 등)을 함께 치료합니다.",
        "prevention": "규칙적인 수면 시간, 카페인/알코올 제한, 취침 전 스마트폰/TV 피하기, 어두운 침실 환경, 낮잠 제한, 규칙적인 운동(단, 취침 전 피하기)이 도움됩니다.",
        "related_drugs": "스틸녹스, 트라조돈, 멜라토닌, 독실아민"
    }
]


async def seed_diseases():
    """질병 데이터 시드"""
    print("🏥 질병 데이터 시드 시작...")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    embedding_service = get_embedding_service()

    async with async_session() as session:
        # 테이블 생성 확인 (Disease, DiseaseVector)
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS diseases (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(500) NOT NULL,
                name_en VARCHAR(500),
                category VARCHAR(200),
                description TEXT,
                causes TEXT,
                symptoms TEXT,
                diagnosis TEXT,
                treatment TEXT,
                prevention TEXT,
                risk_factors TEXT,
                complications TEXT,
                prognosis TEXT,
                related_drugs TEXT,
                data_source VARCHAR(200) DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS disease_vectors (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                disease_id VARCHAR(100) REFERENCES diseases(id) ON DELETE CASCADE,
                embedding vector(1536) NOT NULL,
                document TEXT NOT NULL,
                chunk_index INTEGER DEFAULT 0,
                chunk_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 인덱스 생성
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_diseases_name ON diseases(name)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_disease_vectors_disease_id ON disease_vectors(disease_id)
        """))

        await session.commit()
        print("✅ 테이블 생성/확인 완료")

        # 기존 데이터 삭제
        await session.execute(text("DELETE FROM disease_vectors"))
        await session.execute(text("DELETE FROM diseases"))
        await session.commit()
        print("🗑️ 기존 데이터 삭제 완료")

        # 질병 데이터 삽입
        for disease in SAMPLE_DISEASES:
            await session.execute(text("""
                INSERT INTO diseases (id, name, name_en, category, description, causes, symptoms, diagnosis, treatment, prevention, related_drugs, data_source)
                VALUES (:id, :name, :name_en, :category, :description, :causes, :symptoms, :diagnosis, :treatment, :prevention, :related_drugs, 'manual')
            """), disease)

        await session.commit()
        print(f"✅ {len(SAMPLE_DISEASES)}개 질병 정보 삽입 완료")

        # 벡터 임베딩 생성
        print("🔄 벡터 임베딩 생성 중...")
        vectors_created = 0

        for disease in SAMPLE_DISEASES:
            # 증상 중심 문서 생성
            symptom_doc = f"""
질병명: {disease['name']}
증상: {disease['symptoms']}
원인: {disease['causes']}
치료: {disease['treatment']}
관련 의약품: {disease.get('related_drugs', '')}
"""
            # 전체 정보 문서 생성
            full_doc = f"""
질병명: {disease['name']} ({disease['name_en']})
분류: {disease['category']}
설명: {disease['description']}
원인: {disease['causes']}
증상: {disease['symptoms']}
진단: {disease['diagnosis']}
치료: {disease['treatment']}
예방: {disease['prevention']}
관련 의약품: {disease.get('related_drugs', '')}
"""
            # 증상 문서 임베딩
            symptom_embedding = await embedding_service.embed_text(symptom_doc)
            embedding_str = f"[{','.join(map(str, symptom_embedding))}]"
            await session.execute(text(f"""
                INSERT INTO disease_vectors (disease_id, embedding, document, chunk_index, chunk_type)
                VALUES (:disease_id, '{embedding_str}'::vector, :document, 0, 'symptoms')
            """), {"disease_id": disease["id"], "document": symptom_doc})
            vectors_created += 1

            # 전체 정보 문서 임베딩
            full_embedding = await embedding_service.embed_text(full_doc)
            full_embedding_str = f"[{','.join(map(str, full_embedding))}]"
            await session.execute(text(f"""
                INSERT INTO disease_vectors (disease_id, embedding, document, chunk_index, chunk_type)
                VALUES (:disease_id, '{full_embedding_str}'::vector, :document, 1, 'full')
            """), {"disease_id": disease["id"], "document": full_doc})
            vectors_created += 1

            print(f"  ✅ {disease['name']} 벡터 생성 완료")

        await session.commit()
        print(f"\n🎉 시드 완료! 총 {len(SAMPLE_DISEASES)}개 질병, {vectors_created}개 벡터 생성")


if __name__ == "__main__":
    asyncio.run(seed_diseases())
