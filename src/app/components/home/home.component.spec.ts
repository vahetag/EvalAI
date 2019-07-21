import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { GlobalService } from '../../services/global.service';
import { AuthService } from '../../services/auth.service';
import { EndpointsService } from '../../services/endpoints.service';
import { ApiService } from '../../services/api.service';
import { HomeComponent } from './home.component';
import { HeaderStaticComponent } from '../../components/nav/header-static/header-static.component';
import { FooterComponent } from '../../components/nav/footer/footer.component';
import { ActivatedRoute, Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientModule } from '@angular/common/http';
import { HomemainComponent } from './homemain/homemain.component';
import { PartnersComponent } from './partners/partners.component';
import { RulesComponent } from './rules/rules.component';
import { TestimonialsComponent } from './testimonials/testimonials.component';
import { FeaturedChallengesComponent } from './featured-challenges/featured-challenges.component';
import { TwitterFeedComponent } from './twitter-feed/twitter-feed.component';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { WindowService } from '../../services/window.service';

describe('HomeComponent', () => {
  let component: HomeComponent;
  let fixture: ComponentFixture<HomeComponent>;
  const fakeActivatedRoute = {
    snapshot: { data: { } }
  } as ActivatedRoute;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        HomeComponent,
        HeaderStaticComponent,
        FooterComponent,
        HomemainComponent,
        PartnersComponent,
        RulesComponent,
        TestimonialsComponent,
        FeaturedChallengesComponent,
        TwitterFeedComponent
      ],
      providers: [
        GlobalService,
        AuthService,
        ApiService,
        EndpointsService,
        WindowService
      ],
      imports: [ RouterTestingModule, HttpClientModule ],
      schemas: [ NO_ERRORS_SCHEMA ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(HomeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should be created', () => {
    expect(component).toBeTruthy();
  });

  it(`should have as title 'EvalAI|Home'`, async(() => {
    fixture = TestBed.createComponent(HomeComponent);
    const home = fixture.debugElement.componentInstance;
    expect(home.title).toEqual('EvalAI|Home');
  }));

  it('should render title in a h1 tag', async(() => {
    fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
    const compiled = fixture.debugElement.nativeElement;
    expect(compiled.querySelector('h1').textContent).toContain('EvalAI');
  }));
});
