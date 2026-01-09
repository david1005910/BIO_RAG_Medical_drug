"""Seed sample drug data for testing"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.drug import Drug

# Sample drug data for testing (field names match Drug model)
SAMPLE_DRUGS = [
    {
        "id": "200808876",
        "item_name": "타이레놀정500밀리그램",
        "entp_name": "한국존슨앤드존슨판매(유)",
        "efficacy": "감기로 인한 발열 및 동통(통증), 두통, 신경통, 근육통, 월경통, 염좌통(삔 통증)",
        "use_method": "만 12세 이상 소아 및 성인: 1회 1~2정씩, 1일 3~4회 (4~6시간 마다) 필요시 복용한다.",
        "warning_info": "매일 세잔 이상 정기적으로 술을 마시는 사람이 이 약이나 다른 해열진통제를 복용할 때는 간손상이 유발될 수 있으므로 의사 또는 약사와 상의해야 합니다.",
        "caution_info": "다음 환자에는 투여하지 말 것: 아세트아미노펜 과민증 환자",
        "interaction": "이 약을 복용하는 동안 다른 해열진통제와 함께 복용하지 마세요.",
        "side_effects": "쇽, 아나필락시스양 증상, 중독성표피괴사용해증, 스티븐스-존슨증후군, 급성전신발진농포증",
        "storage_method": "기밀용기, 실온(1~30℃)보관",
    },
    {
        "id": "200502447",
        "item_name": "게보린정",
        "entp_name": "삼진제약(주)",
        "efficacy": "두통, 치통, 발치 후 동통(통증), 인후통(목구멍통증), 귀의 통증, 관절통, 신경통, 요통, 근육통, 어깨결림통증, 타박통, 골절통, 염좌통(삔 통증), 월경통(생리통), 외상통의 진통, 오한, 발열시의 해열",
        "use_method": "성인: 1회 1정, 1일 3회 식후 30분에 복용한다.",
        "warning_info": "이 약에 함유된 이소프로필안티피린에 의해 쇼크(두드러기, 가슴이 답답함, 안면창백, 식은 땀, 손발이 차가워짐)를 일으킬 수 있습니다.",
        "caution_info": "다음 환자에는 투여하지 말 것: 이 약 및 이 약 성분에 과민증 환자",
        "interaction": "이 약을 복용하는 동안 다른 해열진통제를 함께 복용하지 마세요.",
        "side_effects": "쇽, 과민증, 혈액장애(무과립구증, 백혈구감소, 혈소판감소, 혈소판기능저하)",
        "storage_method": "기밀용기, 실온보관",
    },
    {
        "id": "201405348",
        "item_name": "부루펜정400밀리그램",
        "entp_name": "삼일제약(주)",
        "efficacy": "류마티양 관절염, 골관절염(퇴행성 관절질환), 강직성 척추염, 비관절성 류마티스성 질환(건염, 활액낭염, 어깨 통증), 수술 후 동통(통증), 치통",
        "use_method": "이부프로펜으로서 성인: 1일 1200~3200mg을 3~4회 분할 경구투여한다.",
        "warning_info": "심혈관계 혈전증 이상반응의 위험을 증가시킬 수 있으므로 심혈관계 질환 및 위험인자가 있는 환자는 주의해야 합니다.",
        "caution_info": "이 약에 과민반응 및 아스피린 또는 다른 비스테로이드성 소염진통제에 천식, 비염, 혈관부종 또는 두드러기 등의 알레르기 반응이 나타나는 환자",
        "interaction": "아스피린 또는 다른 비스테로이드성 소염진통제와 병용투여 시 위장관 부작용 위험이 증가합니다.",
        "side_effects": "심혈관계: 부종, 체액저류, 혈압상승",
        "storage_method": "기밀용기, 실온(1~30℃)보관",
    },
    {
        "id": "202003672",
        "item_name": "지르텍정10밀리그램",
        "entp_name": "한국유씨비제약(주)",
        "efficacy": "계절성 알레르기 비염, 다년성 알레르기 비염, 알레르기성 결막염, 만성 특발성 두드러기",
        "use_method": "만 12세 이상의 성인 및 소아: 세티리진염산염으로서 1회 10mg을 1일 1회 복용합니다.",
        "warning_info": "졸음이 올 수 있으므로 자동차 운전이나 기계조작 시 주의하세요.",
        "caution_info": "이 약에 과민증 환자, 히드록시진에 과민증 환자, 중증의 신장애 환자(크레아티닌 청소율 10mL/min 미만)",
        "interaction": "중추신경 억제제, 알코올과 병용 시 졸음이 증가할 수 있습니다.",
        "side_effects": "두통, 졸음, 피로감, 구갈, 인두염",
        "storage_method": "기밀용기, 실온보관",
    },
    {
        "id": "200401563",
        "item_name": "베아제정",
        "entp_name": "(주)대웅제약",
        "efficacy": "소화불량, 식욕감퇴, 과식, 체함, 위부팽만감, 소화촉진, 식체, 위약, 구역, 구토",
        "use_method": "성인: 1회 1정, 1일 3회 식후에 복용합니다.",
        "warning_info": "",
        "caution_info": "이 약 성분에 과민증 환자",
        "interaction": "",
        "side_effects": "발진, 가려움증",
        "storage_method": "기밀용기, 실온보관",
    },
    {
        "id": "200704528",
        "item_name": "훼스탈플러스정",
        "entp_name": "한독(주)",
        "efficacy": "소화불량, 식욕감퇴, 과식, 체함, 위부팽만감, 소화촉진",
        "use_method": "성인: 1회 1~2정, 1일 3회 식후에 복용합니다.",
        "warning_info": "",
        "caution_info": "췌장염 환자, 담도 폐쇄 환자",
        "interaction": "",
        "side_effects": "복통, 설사, 변비, 구역",
        "storage_method": "기밀용기, 실온보관",
    },
    {
        "id": "198502177",
        "item_name": "판콜에이내복액",
        "entp_name": "동화약품(주)",
        "efficacy": "감기의 제 증상(콧물, 코막힘, 재채기, 인후통, 기침, 가래, 오한, 발열, 두통, 관절통, 근육통)의 완화",
        "use_method": "만 12세 이상 소아 및 성인: 1회 30mL, 1일 3회 식후 복용",
        "warning_info": "만 2세 미만의 영아에게는 투여하지 마세요.",
        "caution_info": "이 약에 과민반응 환자, MAO 억제제 투여 환자",
        "interaction": "다른 감기약, 해열진통제와 병용하지 마세요.",
        "side_effects": "졸음, 구갈, 어지러움, 변비",
        "storage_method": "기밀용기, 실온보관, 직사광선을 피해 보관",
    },
    {
        "id": "199001234",
        "item_name": "마그밀정",
        "entp_name": "삼진제약(주)",
        "efficacy": "위산과다, 속쓰림, 위부불쾌감, 위부팽만감, 체함, 구역, 구토, 위통, 신트림",
        "use_method": "성인: 1회 1~2정, 1일 3회 식간 또는 취침 전에 복용합니다.",
        "warning_info": "",
        "caution_info": "심한 신장애 환자, 투석 중인 환자",
        "interaction": "일부 항생제(테트라사이클린계, 퀴놀론계)의 흡수를 방해할 수 있습니다.",
        "side_effects": "설사, 고마그네슘혈증",
        "storage_method": "기밀용기, 실온보관",
    },
    {
        "id": "201202156",
        "item_name": "록소닌정60밀리그램",
        "entp_name": "제일약품(주)",
        "efficacy": "관절류마티스, 골관절염, 요통, 어깨관절주위염, 경완비증후군에 의한 진통·소염, 수술 후, 외상 후 및 발치 후의 진통·소염, 급성상기도염(급성인후염, 급성편도염)에서의 진통·해열",
        "use_method": "록소프로펜나트륨으로서 1회 60mg(1정), 1일 3회 식후 경구투여합니다.",
        "warning_info": "소화성 궤양 환자에게는 신중히 투여합니다.",
        "caution_info": "소화성궤양 환자, 중증 혈액이상 환자, 중증 간장애 환자, 중증 신장애 환자, 중증 심부전 환자",
        "interaction": "쿠마린계 항응혈제와 병용 시 그 작용이 증강될 수 있습니다.",
        "side_effects": "쇽, 아나필락시스양 증상, 위장관 출혈",
        "storage_method": "기밀용기, 실온보관",
    },
    {
        "id": "201809234",
        "item_name": "가스모틴정5밀리그램",
        "entp_name": "대웅제약(주)",
        "efficacy": "당뇨병성 위마비증에서 위장기능 이상(속쓰림, 오심, 구토, 복부팽만감, 복통, 식욕부진), 만성위염에서 소화기증상(속쓰림, 오심, 구토, 복부팽만감, 복통, 식욕부진)",
        "use_method": "성인: 모사프리드로서 1회 5mg, 1일 3회 식전 또는 식후에 경구투여합니다.",
        "warning_info": "",
        "caution_info": "이 약에 과민증 환자",
        "interaction": "항콜린제와 병용 시 이 약의 효과가 감소될 수 있습니다.",
        "side_effects": "설사, 연변, 복통, 구역, 구갈",
        "storage_method": "기밀용기, 실온보관",
    },
]


async def seed_data(database_url: str):
    """Insert sample data into database"""
    print("Creating database engine...")
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        print(f"Inserting {len(SAMPLE_DRUGS)} sample drugs...")

        for drug_data in SAMPLE_DRUGS:
            # Check if drug already exists
            result = await session.execute(
                select(Drug).where(Drug.id == drug_data["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  - {drug_data['item_name']} already exists, skipping")
                continue

            drug = Drug(**drug_data)
            session.add(drug)
            print(f"  + {drug_data['item_name']}")

        await session.commit()
        print("Sample data inserted successfully!")

    await engine.dispose()


async def main():
    import os
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/medical_db"
    )

    print(f"Database URL: {database_url}")
    await seed_data(database_url)


if __name__ == "__main__":
    asyncio.run(main())
