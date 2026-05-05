from Library.Universe.Category import CategoryAPI
def test_category_initialization(db):
    cat = CategoryAPI(Primary="Forex", Secondary="Major", db=db)
    assert cat.UID == "Forex (Major)"
    assert cat.Primary == "Forex"
    assert cat.Secondary == "Major"